package dev.guides.java.counterrace;

import java.util.concurrent.locks.ReentrantLock;

public final class LockedCounter {
  private final ReentrantLock lock = new ReentrantLock();
  private long value;

  public LockedCounter(long initialValue) {
    if (initialValue < 0) {
      throw new IllegalArgumentException("initial value must not be negative");
    }
    this.value = initialValue;
  }

  // [Implementation 3] 읽기·판단·쓰기를 하나의 잠금 범위에서 수행합니다.
  public boolean trySubtract(long delta) {
    if (delta <= 0) {
      throw new IllegalArgumentException("delta must be positive");
    }
    lock.lock();
    try {
      if (value < delta) {
        return false;
      }
      value -= delta;
      return true;
    } finally {
      lock.unlock();
    }
  }

  // [Implementation 3-1] 값 조회도 같은 잠금을 사용해 갱신과 겹치지 않게 합니다.
  public long value() {
    lock.lock();
    try {
      return value;
    } finally {
      lock.unlock();
    }
  }
}
