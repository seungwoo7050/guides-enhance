package dev.guides.spring.kafkaavro;

import java.time.Duration;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import org.springframework.stereotype.Component;

@Component
public class EventProbe {
  private final LinkedBlockingQueue<ObservedEvent> events = new LinkedBlockingQueue<>();

  public void record(String key, TaskSubmitted event) {
    events.add(new ObservedEvent(key, event));
  }

  public ObservedEvent poll(Duration timeout) throws InterruptedException {
    return events.poll(timeout.toMillis(), TimeUnit.MILLISECONDS);
  }

  public void clear() {
    events.clear();
  }

  public record ObservedEvent(String key, TaskSubmitted event) {}
}
