package dev.guides.java.counterrace;

import java.util.List;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

public final class DeterministicRaceDemo {
  private static final long INITIAL_VALUE = 100;
  private static final long DELTA = 80;

  private DeterministicRaceDemo() {}

  // [Implementation 2] 두 구현을 실행하고 결과 수집과 실행기 종료를 처리합니다.
  public static void main(String[] arguments) throws Exception {
    ExperimentResult racy = runRacyExperiment();
    ExperimentResult locked = runLockedExperiment();

    print("racy", racy);
    print("locked", locked);
  }

  private static ExperimentResult runRacyExperiment() throws Exception {
    RacyCounter counter = new RacyCounter(INITIAL_VALUE);
    CyclicBarrier barrier = new CyclicBarrier(2);
    ExecutorService executor = Executors.newFixedThreadPool(2);
    try {
      List<Future<Boolean>> results =
          List.of(
              executor.submit(() -> counter.trySubtract(DELTA, barrier)),
              executor.submit(() -> counter.trySubtract(DELTA, barrier)));
      return new ExperimentResult(acceptedAmount(results), counter.value());
    } finally {
      stop(executor);
    }
  }

  private static ExperimentResult runLockedExperiment() throws Exception {
    LockedCounter counter = new LockedCounter(INITIAL_VALUE);
    ExecutorService executor = Executors.newFixedThreadPool(2);
    try {
      List<Future<Boolean>> results =
          List.of(
              executor.submit(() -> counter.trySubtract(DELTA)),
              executor.submit(() -> counter.trySubtract(DELTA)));
      return new ExperimentResult(acceptedAmount(results), counter.value());
    } finally {
      stop(executor);
    }
  }

  private static long acceptedAmount(List<Future<Boolean>> results) throws Exception {
    long accepted = 0;
    for (Future<Boolean> result : results) {
      if (result.get(2, TimeUnit.SECONDS)) {
        accepted += DELTA;
      }
    }
    return accepted;
  }

  private static void stop(ExecutorService executor) throws InterruptedException {
    executor.shutdownNow();
    if (!executor.awaitTermination(2, TimeUnit.SECONDS)) {
      throw new IllegalStateException("executor did not terminate before the deadline");
    }
  }

  private static void print(String label, ExperimentResult result) {
    boolean invariant = result.accepted() + result.value() == INITIAL_VALUE;
    System.out.printf(
        "%s accepted=%d value=%d invariant=%s%n",
        label, result.accepted(), result.value(), invariant);
  }

  private record ExperimentResult(long accepted, long value) {}
}
