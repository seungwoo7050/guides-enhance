package dev.guides.spring.idempotency;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class IdempotencyApplication {
  public static void main(String[] args) {
    SpringApplication.run(IdempotencyApplication.class, args);
  }
}
