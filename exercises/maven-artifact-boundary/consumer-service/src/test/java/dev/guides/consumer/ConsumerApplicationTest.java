package dev.guides.consumer;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class ConsumerApplicationTest {
  @Test
  void readsInstalledContractArtifact() {
    assertEquals("contract=1.0-SNAPSHOT", ConsumerApplication.message());
  }
}
