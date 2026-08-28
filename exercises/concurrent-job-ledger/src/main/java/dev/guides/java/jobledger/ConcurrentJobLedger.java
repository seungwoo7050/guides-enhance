package dev.guides.java.jobledger;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.locks.ReentrantLock;

public final class ConcurrentJobLedger implements AutoCloseable {
  private static final Duration DEFAULT_CLOSE_TIMEOUT = Duration.ofSeconds(5);

  // [Implementation 4] 잔액, 작업 기록, 실행기와 종료 상태의 수명을 원장이 관리합니다.
  private final Clock clock;
  private final ThreadPoolExecutor executor;
  private final ConcurrentHashMap<JobId, JobSlot> jobs = new ConcurrentHashMap<>();
  private final ReentrantLock balanceLock = new ReentrantLock();
  private final AtomicBoolean closed = new AtomicBoolean();

  private long balance;
  private long appliedJobCount;

  public ConcurrentJobLedger(long initialBalance, int workerCount, int queueCapacity, Clock clock) {
    if (initialBalance < 0) {
      throw new IllegalArgumentException("initial balance must not be negative");
    }
    if (workerCount <= 0) {
      throw new IllegalArgumentException("worker count must be positive");
    }
    if (queueCapacity <= 0) {
      throw new IllegalArgumentException("queue capacity must be positive");
    }
    this.balance = initialBalance;
    this.clock = Objects.requireNonNull(clock, "clock is required");
    this.executor =
        new ThreadPoolExecutor(
            workerCount,
            workerCount,
            0L,
            TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<>(queueCapacity),
            new ThreadPoolExecutor.AbortPolicy());
  }

  // [Implementation 5] 다음 잔액과 적용 횟수를 모두 계산한 뒤 함께 반영합니다.
  private JobReceipt apply(JobCommand command) {
    Instant completedAt = clock.instant();
    balanceLock.lock();
    try {
      JobKind kind;
      long nextBalance;
      if (command instanceof CreditJob credit) {
        kind = JobKind.CREDIT;
        nextBalance = Math.addExact(balance, credit.amount());
      } else if (command instanceof DebitJob debit) {
        kind = JobKind.DEBIT;
        if (debit.amount() > balance) {
          throw new IllegalStateException("insufficient balance");
        }
        nextBalance = Math.subtractExact(balance, debit.amount());
      } else {
        throw new IllegalStateException("unsupported job command");
      }

      long nextAppliedJobCount = Math.addExact(appliedJobCount, 1L);
      balance = nextBalance;
      appliedJobCount = nextAppliedJobCount;
      return new JobReceipt(command.id(), kind, command.amount(), nextBalance, completedAt);
    } finally {
      balanceLock.unlock();
    }
  }

  // [Implementation 5-1] 잔액 조회가 갱신 중간 상태를 읽지 않도록 같은 잠금을 사용합니다.
  public long currentBalance() {
    balanceLock.lock();
    try {
      return balance;
    } finally {
      balanceLock.unlock();
    }
  }

  // [Implementation 5-2] 적용 횟수 조회도 잔액과 같은 잠금을 사용합니다.
  public long appliedJobCount() {
    balanceLock.lock();
    try {
      return appliedJobCount;
    } finally {
      balanceLock.unlock();
    }
  }

  // [Implementation 6] 명령과 모든 중복 요청이 공유할 Future를 한 슬롯에 묶습니다.
  private record JobSlot(JobCommand command, CompletableFuture<JobReceipt> result) {}

  // [Implementation 6-1] 작업 성공과 실패를 공유 Future의 완료 결과로 전달합니다.
  private void execute(JobSlot slot) {
    try {
      slot.result().complete(apply(slot.command()));
    } catch (RuntimeException exception) {
      slot.result().completeExceptionally(exception);
    }
  }

  private final class JobTask implements Runnable {
    private final JobSlot slot;

    private JobTask(JobSlot slot) {
      this.slot = slot;
    }

    @Override
    public void run() {
      execute(slot);
    }
  }

  // [Implementation 7] 같은 ID의 중복·충돌을 판정한 뒤 제한된 실행기에 한 번만 제출합니다.
  public CompletableFuture<JobReceipt> submit(JobCommand command) {
    Objects.requireNonNull(command, "command is required");
    if (closed.get()) {
      throw new IllegalStateException("cannot submit work to a closed ledger");
    }

    // 슬롯을 먼저 등록해야 같은 ID를 동시에 제출해도 실제 작업이 하나만 만들어집니다.
    AtomicBoolean created = new AtomicBoolean();
    JobSlot slot =
        jobs.compute(
            command.id(),
            (identifier, existing) -> {
              if (existing == null) {
                created.set(true);
                return new JobSlot(command, new CompletableFuture<>());
              }
              if (!existing.command().equals(command)) {
                throw new IllegalArgumentException(
                    "a job identifier cannot be reused for a different command: "
                        + identifier.value());
              }
              return existing;
            });

    if (created.get()) {
      try {
        executor.execute(new JobTask(slot));
      } catch (RejectedExecutionException exception) {
        // 실행되지 않은 슬롯을 남기면 이후 중복 요청도 끝나지 않은 Future를 받습니다.
        jobs.remove(command.id(), slot);
        slot.result().completeExceptionally(exception);
        throw exception;
      }
    }
    return slot.result();
  }

  // [Implementation 8] 새 작업을 막고 정상 종료를 시도한 뒤 필요하면 남은 작업을 중단합니다.
  public void close(Duration timeout) {
    Objects.requireNonNull(timeout, "close timeout is required");
    if (timeout.isNegative()) {
      throw new IllegalArgumentException("close timeout must not be negative");
    }
    if (!closed.compareAndSet(false, true)) {
      return;
    }

    executor.shutdown();
    long timeoutNanos = timeout.toNanos();
    try {
      if (!executor.awaitTermination(timeoutNanos, TimeUnit.NANOSECONDS)) {
        cancelQueued(executor.shutdownNow());
        if (!executor.awaitTermination(timeoutNanos, TimeUnit.NANOSECONDS)) {
          throw new IllegalStateException("executor did not terminate before the deadline");
        }
      }
    } catch (InterruptedException exception) {
      cancelQueued(executor.shutdownNow());
      // 호출자가 종료 중단을 감지할 수 있도록 인터럽트 상태를 복원합니다.
      Thread.currentThread().interrupt();
      throw new IllegalStateException("executor shutdown was interrupted", exception);
    }
  }

  @Override
  public void close() {
    close(DEFAULT_CLOSE_TIMEOUT);
  }

  // [Implementation 8-1] 시작하지 못한 작업의 Future를 취소 상태로 바꿉니다.
  private static void cancelQueued(List<Runnable> queued) {
    for (Runnable task : queued) {
      if (task instanceof JobTask jobTask) {
        jobTask.slot.result().cancel(false);
      }
    }
  }
}
