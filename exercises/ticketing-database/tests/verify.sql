-- [Implementation 8] 조직 참조, migration, 조회 결과, 제약을 함께 검증합니다.
-- 정확한 결과 집합과 거부되어야 할 INSERT를 실행해 schema와 query가 같은 규칙을 지키는지 확인합니다.
DO $$
DECLARE actual text;
DECLARE priority_validated boolean;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'tickets'
          AND column_name = 'severity'
    ) THEN
        RAISE EXCEPTION 'legacy severity was removed too early';
    END IF;

    SELECT convalidated INTO priority_validated
    FROM pg_constraint
    WHERE conrelid = 'tickets'::regclass
      AND conname = 'tickets_priority_range';
    IF priority_validated IS DISTINCT FROM true THEN
        RAISE EXCEPTION 'priority constraint is not validated';
    END IF;

    SELECT string_agg(format('%s:%s', id, priority), ',' ORDER BY id)
    INTO actual
    FROM tickets;
    IF actual IS DISTINCT FROM '100:5,101:4,102:3,103:2,104:3,200:4' THEN
        RAISE EXCEPTION 'priority backfill mismatch: %', actual;
    END IF;

    SELECT string_agg(
        format('%s:%s:%s', org_id, project_id, open_count),
        ',' ORDER BY org_id, project_id
    )
    INTO actual
    FROM q_project_backlog;
    IF actual IS DISTINCT FROM '1:10:4,2:20:1' THEN
        RAISE EXCEPTION 'backlog mismatch: %', actual;
    END IF;

    SELECT string_agg(id::text, ',' ORDER BY priority DESC, created_at, id)
    INTO actual
    FROM q_assignee_queue
    WHERE org_id = 1
      AND assignee_id = 2;
    IF actual IS DISTINCT FROM '100,101' THEN
        RAISE EXCEPTION 'assignee queue mismatch: %', actual;
    END IF;

    SELECT string_agg(id::text, ',' ORDER BY priority DESC, created_at DESC, id DESC)
    INTO actual
    FROM (
        SELECT id, priority, created_at
        FROM q_org_open_tickets
        WHERE org_id = 1
        ORDER BY priority DESC, created_at DESC, id DESC
        LIMIT 2
    ) AS first_page;
    IF actual IS DISTINCT FROM '100,101' THEN
        RAISE EXCEPTION 'organization first page mismatch: %', actual;
    END IF;

    SELECT string_agg(id::text, ',' ORDER BY priority DESC, created_at DESC, id DESC)
    INTO actual
    FROM (
        SELECT id, priority, created_at
        FROM q_org_open_tickets
        WHERE org_id = 1
          AND (priority, created_at, id)
              < (4, TIMESTAMPTZ '2025-01-02 00:00:00+00', 101)
        ORDER BY priority DESC, created_at DESC, id DESC
        LIMIT 2
    ) AS next_page;
    IF actual IS DISTINCT FROM '104,102' THEN
        RAISE EXCEPTION 'organization keyset page mismatch: %', actual;
    END IF;

    BEGIN
        INSERT INTO tickets(
            id, project_id, org_id, reporter_id, assignee_id,
            title, status, severity, priority, created_at
        ) VALUES (999, 10, 1, 1, 3, 'cross-org assignee', 'OPEN', 'HIGH', 4, now());
        RAISE EXCEPTION 'cross-organization assignee was accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO tickets(
            id, project_id, org_id, reporter_id,
            title, status, severity, priority, created_at
        ) VALUES (998, 10, 1, 1, 'done without time', 'DONE', 'LOW', 2, now());
        RAISE EXCEPTION 'DONE without closed_at was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO tickets(
            id, project_id, org_id, reporter_id,
            title, status, severity, priority, created_at
        ) VALUES (997, 20, 1, 1, 'cross-org project', 'OPEN', 'HIGH', 4, now());
        RAISE EXCEPTION 'cross-organization project was accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO tickets(
            id, project_id, org_id, reporter_id,
            title, status, severity, priority, created_at
        ) VALUES (996, 10, 1, 1, 'bad priority', 'OPEN', 'HIGH', 9, now());
        RAISE EXCEPTION 'out-of-range priority was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
END $$;
