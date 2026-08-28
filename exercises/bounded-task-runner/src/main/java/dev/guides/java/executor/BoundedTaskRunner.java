package dev.guides.java.executor;

import java.time.Duration;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;

public final class BoundedTaskRunner implements AutoCloseable {
  private final ThreadPoolExecutor executor;
  private final Duration shutdownTimeout;

  // [Implementation 1] 작업자 수와 대기열 크기를 고정한 실행기를 생성합니다.
  public BoundedTaskRunner(int workers, int queueCapacity, Duration shutdownTimeout) {
    if (workers < 1) {
      throw new IllegalArgumentException("worker count must be at least one");
    }
    if (queueCapacity < 1) {
      throw new IllegalArgumentException("queue capacity must be at least one");
    }
    this.shutdownTimeout = Objects.requireNonNull(shutdownTimeout, "shutdown timeout is required");
    if (shutdownTimeout.isNegative()) {
      throw new IllegalArgumentException("shutdown timeout must not be negative");
    }

    AtomicInteger sequence = new AtomicInteger();
    executor =
        new ThreadPoolExecutor(
            workers,
            workers,
            0L,
            TimeUnit.MILLISECONDS,
            new ArrayBlockingQueue<>(queueCapacity),
            runnable -> {
              Thread thread = new Thread(runnable, "bounded-task-" + sequence.incrementAndGet());
              thread.setDaemon(false);
              return thread;
            },
            new ThreadPoolExecutor.AbortPolicy());
  }

  // [Implementation 2] 작업 제출 결과와 포화 거절을 호출자에게 그대로 반환합니다.
  public <T> Future<T> submit(Callable<T> task) throws RejectedExecutionException {
    return executor.submit(Objects.requireNonNull(task, "task is required"));
  }

  // [Implementation 3] 제한 시간을 넘긴 Future에 인터럽트 취소를 요청합니다.
  public <T> T run(Callable<T> task, Duration timeout)
      throws InterruptedException, ExecutionException, TimeoutException {
    Objects.requireNonNull(timeout, "task timeout is required");
    if (timeout.isNegative()) {
      throw new IllegalArgumentException("task timeout must not be negative");
    }

    Future<T> future = submit(task);
    try {
      return future.get(timeout.toNanos(), TimeUnit.NANOSECONDS);
    } catch (TimeoutException exception) {
      // 시간 초과를 반환하는 것만으로 작업이 멈추지 않으므로 인터럽트도 요청합니다.
      future.cancel(true);
      throw exception;
    }
  }

  // [Implementation 4] 정상 종료를 먼저 시도하고 필요하면 남은 작업을 강제로 중단합니다.
  @Override
  public void close() {
    executor.shutdown();
    boolean interrupted = false;
    try {
      if (!executor.awaitTermination(shutdownTimeout.toNanos(), TimeUnit.NANOSECONDS)) {
        cancelQueued(executor.shutdownNow());
        if (!executor.awaitTermination(shutdownTimeout.toNanos(), TimeUnit.NANOSECONDS)) {
          throw new IllegalStateException("executor did not terminate before the deadline");
        }
      }
    } catch (InterruptedException exception) {
      interrupted = true;
      cancelQueued(executor.shutdownNow());
    } finally {
      if (interrupted) {
        // 상위 종료 코드가 중단 요청을 확인할 수 있도록 상태를 복원합니다.
        Thread.currentThread().interrupt();
      }
    }
  }

  // [Implementation 4-1] 시작하지 못한 대기 작업의 Future를 취소 상태로 바꿉니다.
  private static void cancelQueued(List<Runnable> queued) {
    for (Runnable task : queued) {
      if (task instanceof Future<?> future) {
        future.cancel(false);
      }
    }
  }
}
