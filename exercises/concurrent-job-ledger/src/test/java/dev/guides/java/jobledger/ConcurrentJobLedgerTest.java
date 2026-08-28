package dev.guides.java.jobledger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CancellationException;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;

class ConcurrentJobLedgerTest {
  private static final Instant COMPLETED_AT = Instant.parse("2026-01-02T03:04:05Z");
  private static final Clock FIXED_CLOCK = Clock.fixed(COMPLETED_AT, ZoneOffset.UTC);

  @Test
  void validatesConstructionAndCommandInvariants() {
    assertThatThrownBy(() -> new JobId(" ")).isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new CreditJob(new JobId("credit"), 0))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new DebitJob(new JobId("debit"), -1))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new ConcurrentJobLedger(-1, 1, 1, FIXED_CLOCK))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new ConcurrentJobLedger(0, 0, 1, FIXED_CLOCK))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new ConcurrentJobLedger(0, 1, 0, FIXED_CLOCK))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void appliesCreditAndDebitWithInjectedClock() throws Exception {
    try (ConcurrentJobLedger ledger = new ConcurrentJobLedger(100, 1, 4, FIXED_CLOCK)) {
      JobReceipt credit =
          ledger.submit(new CreditJob(new JobId("credit-1"), 50)).get(2, TimeUnit.SECONDS);
      JobReceipt debit =
          ledger.submit(new DebitJob(new JobId("debit-1"), 30)).get(2, TimeUnit.SECONDS);

      assertThat(credit)
          .isEqualTo(new JobReceipt(new JobId("credit-1"), JobKind.CREDIT, 50, 150, COMPLETED_AT));
      assertThat(debit.balance()).isEqualTo(120);
      assertThat(debit.completedAt()).isEqualTo(COMPLETED_AT);
      assertThat(ledger.currentBalance()).isEqualTo(120);
      assertThat(ledger.appliedJobCount()).isEqualTo(2);
    }
  }

  @Test
  void sameIdentifierAndCommandShareOneResultAndOneEffect() throws Exception {
    try (ConcurrentJobLedger ledger = new ConcurrentJobLedger(100, 2, 4, FIXED_CLOCK)) {
      CreditJob command = new CreditJob(new JobId("same"), 25);

      CompletableFuture<JobReceipt> first = ledger.submit(command);
      CompletableFuture<JobReceipt> duplicate = ledger.submit(command);

      assertThat(duplicate).isSameAs(first);
      assertThat(first.get(2, TimeUnit.SECONDS).balance()).isEqualTo(125);
      assertThat(ledger.currentBalance()).isEqualTo(125);
      assertThat(ledger.appliedJobCount()).isEqualTo(1);
    }
  }

  @Test
  void concurrentDuplicatesStillShareOneExecution() throws Exception {
    int callerCount = 12;
    CountDownLatch ready = new CountDownLatch(callerCount);
    CountDownLatch start = new CountDownLatch(1);
    ExecutorService callers = Executors.newFixedThreadPool(callerCount);
    try (ConcurrentJobLedger ledger = new ConcurrentJobLedger(100, 2, 4, FIXED_CLOCK)) {
      CreditJob command = new CreditJob(new JobId("concurrent-same"), 25);
      List<Future<CompletableFuture<JobReceipt>>> submissions = new ArrayList<>();
      for (int index = 0; index < callerCount; index++) {
        submissions.add(
            callers.submit(
                () -> {
                  ready.countDown();
                  if (!start.await(5, TimeUnit.SECONDS)) {
                    throw new IllegalStateException("start signal was not released");
                  }
                  return ledger.submit(command);
                }));
      }

      assertThat(ready.await(5, TimeUnit.SECONDS)).isTrue();
      start.countDown();

      CompletableFuture<JobReceipt> shared = submissions.get(0).get(2, TimeUnit.SECONDS);
      for (Future<CompletableFuture<JobReceipt>> submission : submissions) {
        assertThat(submission.get(2, TimeUnit.SECONDS)).isSameAs(shared);
      }
      assertThat(shared.get(2, TimeUnit.SECONDS).balance()).isEqualTo(125);
      assertThat(ledger.appliedJobCount()).isEqualTo(1);
    } finally {
      callers.shutdownNow();
      assertThat(callers.awaitTermination(5, TimeUnit.SECONDS)).isTrue();
    }
  }

  @Test
  void sameIdentifierWithDifferentCommandIsRejected() {
    try (ConcurrentJobLedger ledger = new ConcurrentJobLedger(100, 1, 4, FIXED_CLOCK)) {
      JobId identifier = new JobId("conflict");
      ledger.submit(new CreditJob(identifier, 10));

      assertThatThrownBy(() -> ledger.submit(new CreditJob(identifier, 20)))
          .isInstanceOf(IllegalArgumentException.class)
          .hasMessageContaining("reused for a different command");
    }
  }

  @Test
  void failedDebitLeavesBalanceAndEffectCountUnchanged() {
    try (ConcurrentJobLedger ledger = new ConcurrentJobLedger(20, 1, 4, FIXED_CLOCK)) {
      DebitJob command = new DebitJob(new JobId("too-large"), 30);
      CompletableFuture<JobReceipt> result = ledger.submit(command);
      CompletableFuture<JobReceipt> duplicate = ledger.submit(command);

      assertThat(duplicate).isSameAs(result);
      assertThatThrownBy(() -> result.get(2, TimeUnit.SECONDS))
          .isInstanceOf(ExecutionException.class)
          .hasCauseInstanceOf(IllegalStateException.class);
      assertThat(ledger.currentBalance()).isEqualTo(20);
      assertThat(ledger.appliedJobCount()).isZero();
    }
  }

  @Test
  void overflowLeavesBalanceAndEffectCountUnchanged() {
    try (ConcurrentJobLedger ledger = new ConcurrentJobLedger(Long.MAX_VALUE, 1, 4, FIXED_CLOCK)) {
      CompletableFuture<JobReceipt> result = ledger.submit(new CreditJob(new JobId("overflow"), 1));

      assertThatThrownBy(() -> result.get(2, TimeUnit.SECONDS))
          .isInstanceOf(ExecutionException.class)
          .hasCauseInstanceOf(ArithmeticException.class);
      assertThat(ledger.currentBalance()).isEqualTo(Long.MAX_VALUE);
      assertThat(ledger.appliedJobCount()).isZero();
    }
  }

  @Test
  void boundedQueueRejectsWorkWhenWorkerAndQueueAreOccupied() throws Exception {
    BlockingClock clock = new BlockingClock(COMPLETED_AT);
    try (ConcurrentJobLedger ledger = new ConcurrentJobLedger(0, 1, 1, clock)) {
      CompletableFuture<JobReceipt> running = ledger.submit(new CreditJob(new JobId("running"), 1));
      assertThat(clock.awaitEntry()).isTrue();
      CompletableFuture<JobReceipt> queued = ledger.submit(new CreditJob(new JobId("queued"), 1));

      try {
        assertThatThrownBy(() -> ledger.submit(new CreditJob(new JobId("rejected"), 1)))
            .isInstanceOf(RejectedExecutionException.class);
      } finally {
        clock.release();
      }

      assertThat(running.get(2, TimeUnit.SECONDS).balance()).isEqualTo(1);
      assertThat(queued.get(2, TimeUnit.SECONDS).balance()).isEqualTo(2);
    }
  }

  @Test
  void forcedCloseCancelsWorkThatNeverStarted() throws Exception {
    BlockingClock clock = new BlockingClock(COMPLETED_AT);
    ConcurrentJobLedger ledger = new ConcurrentJobLedger(0, 1, 1, clock);
    CompletableFuture<JobReceipt> running =
        ledger.submit(new CreditJob(new JobId("running-close"), 1));
    assertThat(clock.awaitEntry()).isTrue();
    CompletableFuture<JobReceipt> queued =
        ledger.submit(new CreditJob(new JobId("queued-close"), 1));

    try {
      ledger.close(Duration.ofMillis(100));
    } finally {
      clock.release();
    }

    assertThat(queued).isCancelled();
    assertThatThrownBy(() -> queued.get(2, TimeUnit.SECONDS))
        .isInstanceOf(CancellationException.class);
    assertThatThrownBy(() -> running.get(2, TimeUnit.SECONDS))
        .isInstanceOf(ExecutionException.class)
        .hasCauseInstanceOf(IllegalStateException.class);
  }

  @Test
  void interruptedCloseRestoresInterruptStatusAndStopsAcceptedWork() throws Exception {
    BlockingClock clock = new BlockingClock(COMPLETED_AT);
    ConcurrentJobLedger ledger = new ConcurrentJobLedger(0, 1, 1, clock);
    ledger.submit(new CreditJob(new JobId("blocked-close"), 1));
    assertThat(clock.awaitEntry()).isTrue();

    AtomicReference<Throwable> failure = new AtomicReference<>();
    AtomicBoolean interrupted = new AtomicBoolean();
    Thread closing =
        new Thread(
            () -> {
              Thread.currentThread().interrupt();
              try {
                ledger.close(Duration.ofSeconds(1));
              } catch (Throwable error) {
                failure.set(error);
                interrupted.set(Thread.currentThread().isInterrupted());
              }
            });
    closing.start();
    closing.join(5_000);
    clock.release();

    assertThat(closing.isAlive()).isFalse();
    assertThat(failure.get())
        .isInstanceOf(IllegalStateException.class)
        .hasCauseInstanceOf(InterruptedException.class);
    assertThat(interrupted.get()).isTrue();
  }

  @Test
  void closedLedgerRejectsNewWork() {
    ConcurrentJobLedger ledger = new ConcurrentJobLedger(0, 1, 1, FIXED_CLOCK);
    ledger.close(Duration.ofSeconds(1));

    assertThatThrownBy(() -> ledger.submit(new CreditJob(new JobId("late"), 1)))
        .isInstanceOf(IllegalStateException.class);
  }

  // 작업 스레드를 clock.instant()에서 멈춰 실행 중 작업과 대기 중 작업을 안정적으로 만듭니다.
  private static final class BlockingClock extends Clock {
    private final Instant instant;
    private final CountDownLatch entered = new CountDownLatch(1);
    private final CountDownLatch released = new CountDownLatch(1);

    private BlockingClock(Instant instant) {
      this.instant = instant;
    }

    @Override
    public ZoneId getZone() {
      return ZoneOffset.UTC;
    }

    @Override
    public Clock withZone(ZoneId zone) {
      return this;
    }

    @Override
    public Instant instant() {
      entered.countDown();
      try {
        if (!released.await(5, TimeUnit.SECONDS)) {
          throw new IllegalStateException("test clock was not released");
        }
      } catch (InterruptedException exception) {
        Thread.currentThread().interrupt();
        throw new IllegalStateException("test clock wait was interrupted", exception);
      }
      return instant;
    }

    private boolean awaitEntry() throws InterruptedException {
      return entered.await(5, TimeUnit.SECONDS);
    }

    private void release() {
      released.countDown();
    }
  }
}
