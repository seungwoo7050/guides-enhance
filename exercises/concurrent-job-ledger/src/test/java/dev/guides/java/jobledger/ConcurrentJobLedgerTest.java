package dev.guides.java.jobledger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class ConcurrentJobLedgerTest {

  @Test
  void validatesConstructionAndCommandInvariants() {
    assertThatThrownBy(() -> new JobId(" ")).isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new CreditJob(new JobId("credit"), 0))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> new DebitJob(new JobId("debit"), -1))
        .isInstanceOf(IllegalArgumentException.class);

  }

  // 작업 스레드를 clock.instant()에서 멈춰 실행 중 작업과 대기 중 작업을 안정적으로 만듭니다.
}
