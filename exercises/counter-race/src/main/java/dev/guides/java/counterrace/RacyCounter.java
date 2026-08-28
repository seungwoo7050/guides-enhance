package dev.guides.java.counterrace;

import java.util.Objects;
import java.util.concurrent.BrokenBarrierException;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

public final class RacyCounter {
  private long value;

  public RacyCounter(long initialValue) {
    if (initialValue < 0) {
      throw new IllegalArgumentException("initial value must not be negative");
    }
    this.value = initialValue;
  }

  // [Implementation 1] 읽기·판단·쓰기를 일부러 분리해 손실 갱신을 재현합니다.
  public boolean trySubtract(long delta, CyclicBarrier afterRead) {
    if (delta <= 0) {
      throw new IllegalArgumentException("delta must be positive");
    }
    Objects.requireNonNull(afterRead, "barrier is required");

    long observed = value;
    if (observed < delta) {
      return false;
    }
    // 두 작업이 같은 observed 값을 확보한 뒤에만 쓰기를 시작합니다.
    await(afterRead);
    value = observed - delta;
    return true;
  }

  public long value() {
    return value;
  }

  // [Implementation 1-1] 같은 값을 읽은 두 작업이 모두 도착할 때까지 CyclicBarrier에서 대기합니다.
  private static void await(CyclicBarrier barrier) {
    try {
      barrier.await(2, TimeUnit.SECONDS);
    } catch (InterruptedException exception) {
      Thread.currentThread().interrupt();
      throw new IllegalStateException("barrier wait was interrupted", exception);
    } catch (BrokenBarrierException | TimeoutException exception) {
      throw new IllegalStateException("barrier wait failed", exception);
    }
  }
}
