package dev.guides.java.executor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;
import org.junit.jupiter.api.Test;

class BoundedTaskRunnerTest {
  @Test
  void rejectsWorkWhenWorkerAndQueueAreOccupied() throws Exception {
    CountDownLatch started = new CountDownLatch(1);
    CountDownLatch release = new CountDownLatch(1);
    try (BoundedTaskRunner runner = new BoundedTaskRunner(1, 1, Duration.ofSeconds(1))) {
      runner.submit(
          () -> {
            started.countDown();
            release.await();
            return "running";
          });
      assertThat(started.await(1, TimeUnit.SECONDS)).isTrue();
      runner.submit(() -> "queued");
      try {
        assertThatThrownBy(() -> runner.submit(() -> "rejected"))
            .isInstanceOf(RejectedExecutionException.class);
      } finally {
        release.countDown();
      }
    }
  }

  @Test
  void exposesTaskFailureThroughFuture() throws Exception {
    try (BoundedTaskRunner runner = new BoundedTaskRunner(1, 1, Duration.ofSeconds(1))) {
      var future =
          runner.submit(
              () -> {
                throw new IllegalStateException("task failed");
              });
      assertThatThrownBy(future::get)
          .isInstanceOf(ExecutionException.class)
          .hasCauseInstanceOf(IllegalStateException.class);
    }
  }

}
