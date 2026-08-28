package dev.guides.contract;

// [Implementation 1-1] 소비 모듈이 사용할 공개 버전 값을 제공합니다.
public record ContractVersion(String value) {
  public static ContractVersion current() {
    return new ContractVersion("1.0-SNAPSHOT");
  }
}
