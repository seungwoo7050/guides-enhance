import { sql } from "kysely";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { createDb } from "./db.js";
import { createEvent, reserveSeat, SeatTakenError } from "./repository.js";

const enabled = Boolean(process.env.DATABASE_URL);
const suite = enabled ? describe : describe.skip;

suite("좌석 예약", () => {
  let db: ReturnType<typeof createDb>;

  beforeAll(async () => {
    db = createDb();
  });

  beforeEach(async () => {
    await sql`delete from reservation_audit`.execute(db);
    await db.deleteFrom("reservations").execute();
    await db.deleteFrom("events").execute();
  });

  afterAll(async () => {
    await db.destroy();
  });

  it("같은 좌석을 동시에 예약하면 하나만 성공합니다", async () => {
    const event = await createEvent(db, "Final");
    const results = await Promise.allSettled([
      reserveSeat(db, { eventId: event.id, userId: "a", seatNo: 1 }),
      reserveSeat(db, { eventId: event.id, userId: "b", seatNo: 1 })
    ]);

    expect(results.filter((result) => result.status === "fulfilled")).toHaveLength(1);
    const rejected = results.find((result) => result.status === "rejected");
    expect((rejected as PromiseRejectedResult).reason).toBeInstanceOf(SeatTakenError);
    expect(await rowCount("reservations")).toBe(1);
    expect(await rowCount("reservation_audit")).toBe(1);
  });

  it("감사 기록에 실패하면 예약도 함께 롤백합니다", async () => {
    const event = await createEvent(db, "Rollback final");
    await sql.raw(`
      drop trigger if exists reject_reservation_audit_trigger on reservation_audit;
      drop function if exists reject_reservation_audit();
      create function reject_reservation_audit() returns trigger
      language plpgsql as $$
      begin
        raise exception 'injected audit failure';
      end;
      $$;
      create trigger reject_reservation_audit_trigger
      before insert on reservation_audit
      for each row execute function reject_reservation_audit();
    `).execute(db);
    try {
      await expect(reserveSeat(
        db,
        { eventId: event.id, userId: "rollback-user", seatNo: 7 }
      )).rejects.toThrow("injected audit failure");

      expect(await rowCount("reservations")).toBe(0);
      expect(await rowCount("reservation_audit")).toBe(0);
    } finally {
      await sql.raw(`
        drop trigger if exists reject_reservation_audit_trigger on reservation_audit;
        drop function if exists reject_reservation_audit();
      `).execute(db);
    }
  });

  it("SQL처럼 보이는 입력도 값으로 저장합니다", async () => {
    const eventName = "safe' text'); drop table reservation_audit; --";
    const userId = "user' text'); drop table events; --";
    const event = await createEvent(db, eventName);
    const reservation = await reserveSeat(db, {
      eventId: event.id,
      userId,
      seatNo: 9
    });

    const storedEvent = await db.selectFrom("events")
      .select("name")
      .where("id", "=", event.id)
      .executeTakeFirstOrThrow();
    const storedReservation = await db.selectFrom("reservations")
      .select("user_id")
      .where("id", "=", reservation.id)
      .executeTakeFirstOrThrow();

    expect(storedEvent.name).toBe(eventName);
    expect(storedReservation.user_id).toBe(userId);
    expect(await rowCount("reservation_audit")).toBe(1);
  });

  async function rowCount(table: "reservations" | "reservation_audit") {
    const result = table === "reservations"
      ? await sql<{ count: string }>`select count(*)::text as count from reservations`.execute(db)
      : await sql<{ count: string }>`select count(*)::text as count from reservation_audit`.execute(db);
    return Number(result.rows[0]?.count ?? -1);
  }
});
