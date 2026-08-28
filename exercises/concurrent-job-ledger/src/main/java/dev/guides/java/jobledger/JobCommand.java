package dev.guides.java.jobledger;

// [Implementation 2] 원장이 처리할 명령을 CreditJob과 DebitJob으로 제한합니다.
public sealed interface JobCommand permits CreditJob, DebitJob {
  JobId id();

  long amount();
}
