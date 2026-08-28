package dev.guides.consumer;

import dev.guides.contract.ContractVersion;

// [Implementation 2-1] 설치된 contract-library 산출물의 공개 API를 사용합니다.
public final class ConsumerApplication {
  private ConsumerApplication() {}

  public static String message() {
    return "contract=" + ContractVersion.current().value();
  }
}
