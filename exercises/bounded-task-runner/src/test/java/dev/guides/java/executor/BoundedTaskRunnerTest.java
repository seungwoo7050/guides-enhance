package dev.guides.java.executor;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Duration;
import java.util.concurrent.CancellationException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicBoolean;
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

  @Test
  void cancelsTimedOutTaskWithInterrupt() throws Exception {
    CountDownLatch started = new CountDownLatch(1);
    CountDownLatch interrupted = new CountDownLatch(1);
    try (BoundedTaskRunner runner = new BoundedTaskRunner(1, 1, Duration.ofSeconds(1))) {
      assertThatThrownBy(
              () ->
                  runner.run(
                      () -> {
                        started.countDown();
                        try {
                          new CountDownLatch(1).await();
                        } catch (InterruptedException exception) {
                          interrupted.countDown();
                          throw exception;
                        }
                        return "unreachable";
                      },
                      Duration.ofMillis(50)))
          .isInstanceOf(TimeoutException.class);
      assertThat(started.await(1, TimeUnit.SECONDS)).isTrue();
      assertThat(interrupted.await(1, TimeUnit.SECONDS)).isTrue();
    }
  }

  @Test
  void gracefulClosePreservesAcceptedResult() throws Exception {
    CountDownLatch started = new CountDownLatch(1);
    CountDownLatch release = new CountDownLatch(1);
    AtomicBoolean interrupted = new AtomicBoolean();
    BoundedTaskRunner runner = new BoundedTaskRunner(1, 1, Duration.ofSeconds(1));
    var future =
        runner.submit(
            () -> {
              started.countDown();
              try {
                release.await();
              } catch (InterruptedException exception) {
                interrupted.set(true);
                throw exception;
              }
              return "completed";
            });
    assertThat(started.await(1, TimeUnit.SECONDS)).isTrue();
    Thread releaser =
        new Thread(
            () -> {
              try {
                TimeUnit.MILLISECONDS.sleep(50);
              } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
              } finally {
                release.countDown();
              }
            },
            "graceful-close-release");

    releaser.start();
    runner.close();
    releaser.join(1_000);

    assertThat(releaser.isAlive()).isFalse();
    assertThat(interrupted.get()).isFalse();
    assertThat(future.get(1, TimeUnit.SECONDS)).isEqualTo("completed");
  }

  @Test
  void forcedCloseInterruptsRunningWorkAndCancelsQueuedFuture() throws Exception {
    CountDownLatch started = new CountDownLatch(1);
    CountDownLatch interrupted = new CountDownLatch(1);
    BoundedTaskRunner runner = new BoundedTaskRunner(1, 1, Duration.ofMillis(200));
    try {
      var running =
          runner.submit(
              () -> {
                started.countDown();
                try {
                  new CountDownLatch(1).await();
                } catch (InterruptedException exception) {
                  interrupted.countDown();
                  throw exception;
                }
                return "unreachable";
              });
      assertThat(started.await(1, TimeUnit.SECONDS)).isTrue();
      var queued = runner.submit(() -> "queued");

      runner.close();

      assertThat(interrupted.await(1, TimeUnit.SECONDS)).isTrue();
      assertThatThrownBy(() -> running.get(1, TimeUnit.SECONDS))
          .isInstanceOf(ExecutionException.class)
          .hasCauseInstanceOf(InterruptedException.class);
      assertThat(queued.isCancelled()).isTrue();
      assertThatThrownBy(() -> queued.get(1, TimeUnit.SECONDS))
          .isInstanceOf(CancellationException.class);
    } finally {
      runner.close();
    }
  }

  @Test
  void interruptedCloseRestoresStatusAndCancelsQueuedFuture() throws Exception {
    CountDownLatch started = new CountDownLatch(1);
    CountDownLatch interrupted = new CountDownLatch(1);
    AtomicBoolean restored = new AtomicBoolean();
    BoundedTaskRunner runner = new BoundedTaskRunner(1, 1, Duration.ofSeconds(1));
    try {
      var running =
          runner.submit(
              () -> {
                started.countDown();
                try {
                  new CountDownLatch(1).await();
                } catch (InterruptedException exception) {
                  interrupted.countDown();
                  throw exception;
                }
                return "unreachable";
              });
      assertThat(started.await(1, TimeUnit.SECONDS)).isTrue();
      var queued = runner.submit(() -> "queued");
      Thread closer =
          new Thread(
              () -> {
                Thread.currentThread().interrupt();
                runner.close();
                restored.set(Thread.currentThread().isInterrupted());
              },
              "interrupted-runner-close");

      closer.start();
      closer.join(1_000);

      assertThat(closer.isAlive()).isFalse();
      assertThat(restored.get()).isTrue();
      assertThat(interrupted.await(1, TimeUnit.SECONDS)).isTrue();
      assertThatThrownBy(() -> running.get(1, TimeUnit.SECONDS))
          .isInstanceOf(ExecutionException.class)
          .hasCauseInstanceOf(InterruptedException.class);
      assertThat(queued.isCancelled()).isTrue();
      assertThatThrownBy(() -> queued.get(1, TimeUnit.SECONDS))
          .isInstanceOf(CancellationException.class);
    } finally {
      runner.close();
    }
  }
}
