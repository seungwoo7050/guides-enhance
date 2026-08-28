package dev.guides.java.executor;

import java.time.Duration;
import java.util.Objects;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.Future;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
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

  @Override
  public void close() { executor.shutdown(); }
}
