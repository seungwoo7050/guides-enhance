package dev.guides.spring.boundaries;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class BoundaryApplication {
  public static void main(String[] args) {
    SpringApplication.run(BoundaryApplication.class, args);
  }
}
