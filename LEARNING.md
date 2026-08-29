# Learning Path

이 문서는 42 과제, 개발자 공통 기본소양, 웹 개발, 게임 서버 개발을 하나의 학습 경로로 정리합니다.

목표는 가이드를 먼저 완주하는 것이 아닙니다.

> 최소 문서로 프로젝트에 진입합니다.
> → 프로젝트 경험이 쌓이고 시간이 지난 뒤 exercise의 요구사항과 테스트만 보고 다시 구현합니다.
> → 실패한 영역의 문서만 다시 읽습니다.

구현 도중 참고할 문서 목록은 이 문서에서 관리하지 않습니다. 실제 프로젝트의 요구사항과 현재 막힌 문제를 기준으로 필요한 자료를 직접 찾습니다.

## 기준

* **필수 문서**: 해당 프로젝트 또는 학습 트랙을 시작하기 전에 읽습니다.
* **필수 exercise**: 해당 트랙의 핵심 역량을 다시 확인하기 위해 구현합니다.
* **필요 exercise**: 특정 직무, 스택 또는 약점과 연결될 때 구현합니다.
* exercise는 선행 과제가 아닙니다.
* exercise를 구현할 때는 해당 가이드와 기존 구현을 보지 않습니다.
* `docs/00-roadmap.md`는 각 브랜치의 전체 구성을 확인하는 목차로만 사용하며 아래 문서 목록에서는 생략합니다.
* 어떤 필수 exercise가 특정 언어로 작성되어 있고 해당 언어의 가이드 브랜치가 존재한다면 그 언어 가이드도 학습 경로에 포함합니다.

---

# 1. 전체 브랜치 구성

| 브랜치                  | 42    | 공통 기본소양 | 웹 개발 | 게임 서버 |
| ----------------------- | :---: | :-----------: | :-----: | :-------: |
| `c`                     |  필수 |               |         | 필요      |
| `cpp`                   |  필수 |               |         | 필수      |
| `network`               |  필수 | 필수          | 필수    | 필수      |
| `web-infra`             |  필수 |               | 필수    |           |
| `web-basic`             |  필수 |               | 필수    |           |
| `frontend-react-nextjs` |  필수 |               | 필수    |           |
| `game-server`           |  필요 |               |         | 필수      |
| `git`                   |       | 필수          | 필수    | 필수      |
| `python`                |       | 필수¹         |         |           |
| `java`                  |       | 필요¹         | 필요    | 필요¹     |
| `algorithm`             |       | 필수          | 필요    | 필수      |
| `computer-architecture` |       | 필수          | 필요    | 필수      |
| `os`                    |       | 필수          | 필요    | 필수      |
| `db`                    |       | 필수          | 필수    | 필요      |
| `security`              |       | 필수          | 필수    | 필수      |
| `backend-spring`        |       |               | 필요    |           |
| `distributed-services`  |       |               | 필수    | 필수      |
| `cloud-computing`       |       |               | 필수    | 필수      |

¹ 다른 필수 exercise의 구현 언어이므로 포함합니다.

---

# 2. 42 트랙

진행 대상은 다음과 같습니다.

```text
Libft
→ ft_printf
→ get_next_line
→ Born2beroot
→ push_swap
→ minitalk / pipex
→ Philosophers
→ minishell
→ NetPractice
→ CPP Module 00~04
→ miniRT (Modern C++)
→ CPP Module 05~09
→ ft_irc
→ webserv
→ Inception
→ ft_transcendence
```

`so_long`, `FdF`, `fract-ol` 계열 과제는 진행하지 않습니다.

---

## 2.1 C

### Libft 시작 전

다음 8개만 먼저 읽습니다.

```text
c/docs/01-foundations/01-edit-compile-run.md
c/docs/01-foundations/02-values-branches-loops.md
c/docs/01-foundations/03-functions-arrays-text.md
c/docs/01-foundations/04-input-errors-debugging.md

c/docs/02-c-language/01-c-program-model.md
c/docs/02-c-language/02-memory-pointers-strings.md
c/docs/02-c-language/03-data-structures-api-design.md
c/docs/02-c-language/04-build-link-test.md
```

### 과제 시작 전 추가 문서

| 과제            | 최소 추가 문서                                                                 |
| --------------- | ------------------------------------------------------------------------------ |
| `ft_printf`     | `c/docs/02-c-language/05-variadic-format-api.md`                               |
| `get_next_line` | `c/docs/03-unix-programming/01-posix-io-streams.md`                            |
| `minitalk`      | `c/docs/03-unix-programming/03-signals-events.md`                              |
| `pipex`         | `c/docs/03-unix-programming/02-process-fd-pipe.md`                             |
| `Philosophers`  | `c/docs/03-unix-programming/05-threads-time.md`                                |
| `minishell`     | `02-process-fd-pipe.md`, `03-signals-events.md`, `04-shell-parser-executor.md` |
| `push_swap`     | 추가 선행 문서 없음                                                            |
| `Born2beroot`   | 대응 가이드 없음                                                               |

### Exercise

| 구분 | Exercise                           | 주요 복습 대상                    |
| ---- | ---------------------------------- | --------------------------------- |
| 필수 | `c/exercises/owned-string`         | Libft, GNL, Minishell             |
| 필수 | `c/exercises/diagnostic-formatter` | ft_printf                         |
| 필수 | `c/exercises/record-stream`        | get_next_line                     |
| 필수 | `c/exercises/signal-loop`          | minitalk, minishell               |
| 필수 | `c/exercises/command-runner`       | pipex, minishell                  |
| 필수 | `c/exercises/account-simulator`    | Philosophers                      |
| 필요 | `c/exercises/int-vector`           | 동적 배열과 메모리 관리가 약할 때 |
| 필요 | `c/exercises/command-pipeline`     | pipe와 FD 관리가 약할 때          |

---

## 2.2 Network

### NetPractice 시작 전

```text
network/docs/01-link-and-path/01-layers-encapsulation-and-path.md
network/docs/01-link-and-path/02-ethernet-mac-and-switching.md
network/docs/01-link-and-path/03-arp-and-neighbor-discovery.md

network/docs/02-internetworking/01-ip-addressing-subnets-and-lpm.md
network/docs/02-internetworking/02-ip-forwarding-mtu-and-icmp.md
```

### ft_irc / webserv 시작 전

```text
network/docs/03-transport/01-udp-and-tcp-service-contracts.md
network/docs/03-transport/02-tcp-connection-state-and-sequences.md
```

### Exercise

| 구분                   | Exercise                               |
| ---------------------- | -------------------------------------- |
| 필수                   | `network/exercises/protocol-inspector` |
| 필요                   | `network/exercises/path-diagnosis`     |
| 공통 기본소양에서 필수 | `network/exercises/linux-routing-nat`  |

---

## 2.3 C++

### Modern C++ 기본

```text
cpp/docs/01-modern-cpp/01-program-build-cmake.md
cpp/docs/01-modern-cpp/02-values-lifetimes-and-move.md
cpp/docs/01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md
cpp/docs/01-modern-cpp/04-classes-responsibilities-and-polymorphism.md
cpp/docs/01-modern-cpp/05-errors-optional-variant-and-expected.md
cpp/docs/01-modern-cpp/06-algorithms-ranges-templates-and-concepts.md
```

miniRT는 이 기반을 사용해 Modern C++로 구현합니다.

### C++98 기본

```text
cpp/docs/90-appendix/01-modern-to-cpp98-crosswalk.md

cpp/docs/02-cpp98-systems/01-program-and-type-model.md
cpp/docs/02-cpp98-systems/02-lifetime-value-and-ownership.md
cpp/docs/02-cpp98-systems/03-assigning-object-responsibilities.md
cpp/docs/02-cpp98-systems/04-inheritance-and-polymorphism.md
cpp/docs/02-cpp98-systems/05-errors-validation-and-casts.md
cpp/docs/02-cpp98-systems/06-templates-iterators-and-stl.md
```

CPP Module은 C++98 기반으로 구현합니다.

### ft_irc 시작 전

```text
cpp/docs/02-cpp98-systems/08-posix-sockets-and-event-loop.md
```

### webserv 시작 전

```text
cpp/docs/02-cpp98-systems/08-posix-sockets-and-event-loop.md
cpp/docs/02-cpp98-systems/09-object-oriented-http-server.md
```

### Exercise

| 구분 | Exercise                         | 주요 복습 대상                    |
| ---- | -------------------------------- | --------------------------------- |
| 필수 | `cpp/exercises/mini-vector`      | 객체 수명, template, container    |
| 필수 | `cpp/exercises/command-service`  | C++98 객체 설계와 오류 처리       |
| 필수 | `cpp/exercises/line-server`      | ft_irc, webserv                   |
| 필요 | `cpp/exercises/local-job-runner` | 게임 서버, queue, 취소, 동시 종료 |

---

## 2.4 Inception

### 시작 전

```text
web-infra/docs/01-foundations/01-web-request-and-server.md
web-infra/docs/01-foundations/02-docker-image-and-container.md
web-infra/docs/01-foundations/03-compose-network-and-storage.md
```

### Exercise

| 구분 | Exercise                          |
| ---- | --------------------------------- |
| 필수 | `web-infra/exercises/notes-stack` |

---

## 2.5 ft_transcendence

### 웹 기본

```text
web-basic/docs/01-web-foundations/01-how-the-web-works.md
web-basic/docs/01-web-foundations/02-html-forms-accessibility.md
web-basic/docs/01-web-foundations/03-css-layout-responsive.md
web-basic/docs/01-web-foundations/04-javascript-foundations.md
web-basic/docs/01-web-foundations/05-dom-events-url-storage.md
web-basic/docs/01-web-foundations/06-async-fetch-errors.md
web-basic/docs/01-web-foundations/07-typescript-runtime-validation.md
web-basic/docs/01-web-foundations/08-node-packages-workspaces.md
```

### React / Next.js 기본

```text
frontend-react-nextjs/docs/01-project-onboarding.md
frontend-react-nextjs/docs/02-ui-and-state-architecture.md
```

### Exercise

| 구분 | Exercise                                          |
| ---- | ------------------------------------------------- |
| 필수 | `frontend-react-nextjs/exercises/project-catalog` |
| 필수 | `web-basic/exercises/session-access-control`      |
| 필수 | `web-basic/exercises/realtime-board`              |
| 필요 | `web-basic/exercises/notes-api`                   |
| 필요 | `web-basic/exercises/seat-reservation`            |
| 필요 | `web-basic/exercises/user-directory`              |
| 필요 | `web-basic/exercises/runtime-workspace`           |
| 필요 | `web-basic/exercises/browser-directory`           |

---

## 2.6 서버 권위형 Pong을 구현하는 경우

ft_transcendence의 Pong 서버가 클라이언트 입력을 받아 서버에서 경기 상태를 계산한다면 다음 문서를 추가합니다.

```text
game-server/docs/01-authoritative-state-and-trust.md
game-server/docs/02-tick-time-and-command-order.md
game-server/docs/03-connection-session-room-and-match-lifecycle.md
game-server/docs/04-transport-protocol-and-state-replication.md
```

### Exercise

| 구분 | Exercise                                       |
| ---- | ---------------------------------------------- |
| 필수 | `game-server/exercises/tick-command-model`     |
| 필요 | `game-server/exercises/session-room-lifecycle` |
| 필요 | `game-server/exercises/replication-reconnect`  |

`load-placement`, `trust-abuse`는 게임 서버 직무 트랙에서 수행합니다.

---

# 3. 개발자 공통 기본소양

다음 과정은 42 프로젝트를 시작하기 위한 선행 조건이 아닙니다.

42를 진행하면서 별도 학습 트랙으로 수행합니다.

---

## 3.1 Git

### 필수 문서

```text
git/docs/01-workspace-basics.md
git/docs/02-commit-workflow.md
git/docs/03-remote-pr-workflow.md
git/docs/04-merge-rebase-conflicts.md
git/docs/05-recovery-runbook.md
git/docs/06-github-actions-workflow-model.md
git/docs/07-pull-request-ci-and-security.md
```

### Exercise

| 구분 | Exercise                          |
| ---- | --------------------------------- |
| 필수 | `git/exercises/local-git-lab`     |
| 필수 | `git/exercises/github-actions-ci` |

---

## 3.2 Python

여러 기본소양 가이드의 exercise가 Python으로 구현되어 있으므로 포함합니다.

### 필수 문서

```text
python/docs/01-language-and-runtime/01-runtime-and-environment.md
python/docs/01-language-and-runtime/02-objects-and-collections.md
python/docs/01-language-and-runtime/03-functions-errors-and-types.md
python/docs/01-language-and-runtime/04-iterators-generators-and-context-managers.md

python/docs/02-automation/01-files-structured-data-and-cli.md

python/docs/03-quality/01-testing.md
python/docs/03-quality/02-project-structure-packaging-and-typing.md
```

### Exercise

| 구분 | Exercise                           |
| ---- | ---------------------------------- |
| 필수 | `python/exercises/data-report`     |
| 필요 | `python/exercises/command-checker` |

---

## 3.3 Algorithm

### 필수 문서

```text
algorithm/docs/01-foundations/01-problem-contracts-and-counterexamples.md
algorithm/docs/01-foundations/02-asymptotic-analysis.md
algorithm/docs/01-foundations/03-recurrences-and-divide-and-conquer.md
algorithm/docs/01-foundations/04-correctness-and-invariants.md

algorithm/docs/02-data-structures/01-linear-structures-ranges-and-hashing.md
algorithm/docs/02-data-structures/02-order-search-heaps-and-priority.md
algorithm/docs/02-data-structures/03-trees-and-balanced-search-trees.md
algorithm/docs/02-data-structures/04-disjoint-sets-and-amortized-analysis.md

algorithm/docs/03-design-techniques/01-brute-force-and-backtracking.md
algorithm/docs/03-design-techniques/02-greedy-methods.md
algorithm/docs/03-design-techniques/03-dynamic-programming.md

algorithm/docs/04-graph-algorithms/01-traversal-and-topological-order.md
algorithm/docs/04-graph-algorithms/02-minimum-spanning-trees.md
algorithm/docs/04-graph-algorithms/03-shortest-paths.md
algorithm/docs/04-graph-algorithms/04-network-flow-and-matching.md

algorithm/docs/05-string-algorithms/01-string-matching-and-preprocessing.md

algorithm/docs/06-complexity/01-sorting-stability-and-lower-bounds.md
```

### Exercise

| 구분 | Exercise                                  |
| ---- | ----------------------------------------- |
| 필수 | `algorithm/exercises/verified-algorithms` |

---

## 3.4 Computer Architecture

### 필수 문서

```text
computer-architecture/docs/01-representation-and-isa/01-data-representation-and-arithmetic.md
computer-architecture/docs/01-representation-and-isa/02-isa-assembly-and-program-execution.md
computer-architecture/docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md

computer-architecture/docs/02-in-order-execution/04-datapath-and-control.md
computer-architecture/docs/02-in-order-execution/05-pipeline-hazards-and-branching.md

computer-architecture/docs/03-memory-hierarchy/06-cache-locality-and-amat.md
computer-architecture/docs/03-memory-hierarchy/07-address-translation-and-tlb.md

computer-architecture/docs/04-parallel-execution/08-superscalar-out-of-order-and-speculation.md
computer-architecture/docs/04-parallel-execution/10-multicore-coherence-and-false-sharing.md
```

### Exercise

| 구분 | Exercise                                          |
| ---- | ------------------------------------------------- |
| 필수 | `computer-architecture/exercises/processor-model` |

---

## 3.5 Operating Systems

### 필수 문서

```text
os/docs/01-boundary-and-execution/01-kernel-boundary-and-events.md
os/docs/01-boundary-and-execution/02-processes-threads-and-context-switches.md
os/docs/01-boundary-and-execution/03-cpu-scheduling.md
os/docs/01-boundary-and-execution/04-blocking-wakeup-and-ipc.md

os/docs/02-concurrency/01-races-atomicity-and-ordering.md
os/docs/02-concurrency/02-synchronization-primitives.md
os/docs/02-concurrency/03-deadlock-and-progress.md

os/docs/03-virtual-memory/01-address-spaces-and-faults.md
os/docs/03-virtual-memory/02-demand-paging-cow-and-replacement.md

os/docs/04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md
os/docs/04-storage-and-io/02-device-io-interrupts-and-dma.md
```

### Exercise

| 구분 | Exercise                    |
| ---- | --------------------------- |
| 필수 | `os/exercises/kernel-model` |

---

## 3.6 Network — 기본소양 완성

42에서 이미 읽은 문서는 다시 읽지 않습니다.

### 추가 필수 문서

```text
network/docs/02-internetworking/03-nat-connection-tracking-and-firewalls.md
network/docs/02-internetworking/04-routing-algorithms-and-protocols.md

network/docs/03-transport/03-retransmission-rtt-and-sliding-windows.md
network/docs/03-transport/04-flow-and-congestion-control.md

network/docs/04-application-security-and-evidence/01-dns-http-tls-and-quic.md
network/docs/04-application-security-and-evidence/02-network-failure-localization.md
```

### 추가 Exercise

| 구분 | Exercise                              |
| ---- | ------------------------------------- |
| 필수 | `network/exercises/linux-routing-nat` |
| 필수 | `network/exercises/path-diagnosis`    |

`protocol-inspector`는 42 복습 과정에서 이미 수행합니다.

---

## 3.7 Database Systems

### 필수 문서

```text
db/docs/01-relational-semantics-and-design/01-relational-model-and-algebra.md
db/docs/01-relational-semantics-and-design/02-sql-semantics-and-query-shape.md
db/docs/01-relational-semantics-and-design/03-er-normalization-and-constraints.md

db/docs/02-storage-and-indexes/01-pages-records-and-files.md
db/docs/02-storage-and-indexes/02-index-structures.md
db/docs/02-storage-and-indexes/03-buffer-pool-and-replacement.md

db/docs/03-transactions-and-recovery/01-transactions-isolation-and-locks.md
db/docs/03-transactions-and-recovery/02-mvcc-wal-and-recovery.md

db/docs/04-execution-and-optimization/01-query-execution-joins-and-sorting.md
db/docs/04-execution-and-optimization/02-statistics-cost-model-and-explain.md
db/docs/04-execution-and-optimization/03-schema-index-and-tuning-loop.md

db/docs/90-system-review.md
```

### Exercise

| 구분 | Exercise                                   |
| ---- | ------------------------------------------ |
| 필수 | `db/exercises/sql-semantics-views`         |
| 필수 | `db/exercises/ticketing-database`          |
| 필수 | `db/exercises/slotted-page`                |
| 필수 | `db/exercises/bplus-tree`                  |
| 필수 | `db/exercises/clock-buffer-pool`           |
| 필수 | `db/exercises/postgres-concurrency-guards` |
| 필수 | `db/exercises/wal-recovery-simulator`      |
| 필수 | `db/exercises/join-algorithms`             |
| 필수 | `db/exercises/postgres-workload-indexes`   |
| 필요 | `db/exercises/mini-storage-engine`         |

---

## 3.8 Security

### 필수 문서

```text
security/docs/01-security-state-and-evidence.md
security/docs/02-assets-trust-boundaries-and-threat-models.md
security/docs/03-scope-authorization-and-rules-of-engagement.md

security/docs/04-risk-vulnerability-and-prioritization.md
security/docs/06-application-boundary-failures.md
security/docs/07-system-identity-and-secret-boundaries.md

security/docs/10-security-requirements-and-design-invariants.md
security/docs/11-security-testing-and-assurance.md
security/docs/12-remediation-hardening-and-regression.md

security/docs/13-telemetry-detection-and-investigation.md
security/docs/14-incident-response-and-recovery.md
```

### Exercise

| 구분 | Exercise                              |
| ---- | ------------------------------------- |
| 필수 | `security/exercises/ledgerlab-policy` |

---

# 4. Java 기반 실습을 위한 기본 과정

`distributed-services`의 필수 exercise와 `backend-spring`을 진행할 수 있도록 Java를 포함합니다.

## Java

### 필수 문서

```text
java/docs/01-language-and-domain/01-jdk-jvm-and-first-program.md
java/docs/01-language-and-domain/02-java-language-foundations.md
java/docs/01-language-and-domain/03-domain-types-records-and-sealed-types.md
java/docs/01-language-and-domain/04-collections-streams-and-numeric-invariants.md
java/docs/01-language-and-domain/05-errors-validation-time-and-identifiers.md

java/docs/02-runtime-and-concurrency/01-concurrency-locking-and-executors.md

java/docs/03-build-test-and-evidence/01-maven-wrapper-and-lifecycle.md
java/docs/03-build-test-and-evidence/02-junit-assertj-and-test-doubles.md
```

### Exercise

| 구분 | Exercise                               |
| ---- | -------------------------------------- |
| 필수 | `java/exercises/number-report`         |
| 필수 | `java/exercises/counter-race`          |
| 필수 | `java/exercises/bounded-task-runner`   |
| 필수 | `java/exercises/concurrent-job-ledger` |

---

# 5. 웹 개발자 추가 트랙

42의 `web-basic`, `frontend-react-nextjs`, `web-infra`와 공통 기본소양의 `network`, `db`, `security`는 이미 포함되어 있습니다.

웹 개발자 트랙에서는 다음 내용을 추가합니다.

---

## 5.1 Backend Spring

Java/Spring 백엔드를 사용할 경우 진행합니다.

### 프로젝트 시작 전 최소 문서

```text
backend-spring/docs/01-spring-core/01-application-context-and-lifecycle.md
backend-spring/docs/01-spring-core/02-configuration-profiles-and-readiness.md
backend-spring/docs/02-web-and-security/01-mvc-validation-and-problem-detail.md
```

### Exercise

| 구분 | Exercise                                               |
| ---- | ------------------------------------------------------ |
| 필수 | `backend-spring/exercises/request-preview-api`         |
| 필수 | `backend-spring/exercises/project-access-api`          |
| 필수 | `backend-spring/exercises/inventory-reservation`       |
| 필수 | `backend-spring/exercises/policy-decision-client`      |
| 필요 | `backend-spring/exercises/idempotent-operation-outbox` |
| 필요 | `backend-spring/exercises/kafka-avro-contract`         |

---

## 5.2 Distributed Services

웹 백엔드와 게임 서버가 공통으로 사용하는 후속 과정입니다.

### 필수 문서

```text
distributed-services/docs/01-boundaries-and-failure/01-partial-failure-and-uncertain-outcomes.md
distributed-services/docs/01-boundaries-and-failure/02-service-boundaries-and-data-ownership.md
distributed-services/docs/01-boundaries-and-failure/03-synchronous-and-asynchronous-decisions.md

distributed-services/docs/02-delivery-and-consistency/01-idempotency-and-single-effects.md
distributed-services/docs/02-delivery-and-consistency/02-outbox-saga-and-reconciliation.md
distributed-services/docs/02-delivery-and-consistency/03-contracts-versioning-and-order.md
distributed-services/docs/02-delivery-and-consistency/04-read-models-and-late-events.md

distributed-services/docs/03-resilience-and-load/01-timeouts-retries-circuit-breakers-and-dlq.md
distributed-services/docs/03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md

distributed-services/docs/04-release-and-evidence/02-distributed-observability.md
```

### Exercise

| 구분 | Exercise                                                   |
| ---- | ---------------------------------------------------------- |
| 필수 | `distributed-services/exercises/service-boundary`          |
| 필수 | `distributed-services/exercises/request-decision`          |
| 필수 | `distributed-services/exercises/outbox-reconciliation`     |
| 필수 | `distributed-services/exercises/contracts-and-order`       |
| 필수 | `distributed-services/exercises/read-model-rebuild`        |
| 필수 | `distributed-services/exercises/retry-budget`              |
| 필수 | `distributed-services/exercises/backpressure`              |
| 필수 | `distributed-services/exercises/observability-correlation` |
| 필수 | `distributed-services/exercises/reservation-flow`          |

---

## 5.3 Cloud Computing

웹 개발자와 게임 서버 개발자가 공통으로 진행합니다.

### 필수 문서

```text
cloud-computing/docs/01-cloud-state-responsibility-and-evidence.md
cloud-computing/docs/02-cloud-characteristics-service-and-deployment-models.md
cloud-computing/docs/03-control-plane-data-plane-and-identity.md
cloud-computing/docs/04-iaas-compute-network-and-storage.md

cloud-computing/docs/05-failure-domains-elasticity-and-recovery.md
cloud-computing/docs/06-paas-and-managed-service-contracts.md
cloud-computing/docs/07-serverless-and-faas-runtime.md
cloud-computing/docs/08-event-delivery-concurrency-and-idempotency.md
cloud-computing/docs/09-saas-tenancy-and-isolation.md

cloud-computing/docs/11-cloud-security-observability-and-incidents.md
cloud-computing/docs/12-cost-capacity-quotas-and-finops.md
cloud-computing/docs/14-service-selection-and-architecture-review.md
```

### Exercise

| 구분 | Exercise                                      |
| ---- | --------------------------------------------- |
| 필수 | `cloud-computing/exercises/local-cloud-model` |

---

# 6. 게임 서버 개발자 추가 트랙

42의 C++, Network와 공통 기본소양의 Algorithm, Computer Architecture, OS, Security를 기반으로 합니다.

여기에 `game-server`, `distributed-services`, `cloud-computing`을 추가합니다.

---

## Game Server

### 필수 문서

```text
game-server/docs/01-authoritative-state-and-trust.md
game-server/docs/02-tick-time-and-command-order.md
game-server/docs/03-connection-session-room-and-match-lifecycle.md
game-server/docs/04-transport-protocol-and-state-replication.md
game-server/docs/07-load-backpressure-placement-and-handover.md
game-server/docs/08-security-abuse-and-anticheat-boundaries.md
game-server/docs/09-testing-observability-and-release-evidence.md
```

### Exercise

| 구분 | Exercise                                       |
| ---- | ---------------------------------------------- |
| 필수 | `game-server/exercises/tick-command-model`     |
| 필수 | `game-server/exercises/session-room-lifecycle` |
| 필수 | `game-server/exercises/replication-reconnect`  |
| 필수 | `game-server/exercises/load-placement`         |
| 필수 | `game-server/exercises/trust-abuse`            |

이 exercise들은 Python으로 구현되어 있으므로 `python` 가이드가 전체 경로에 포함됩니다.

---

# 7. 최종 경로 요약

## 42

```text
C 최소 기반
→ C 과제
→ Network 최소 기반
→ NetPractice
→ C++ 최소 기반
→ C++ 과제 / miniRT / ft_irc / webserv
→ Web Infra 최소 기반
→ Inception
→ Web 기본 + React/Next.js 최소 기반
→ ft_transcendence
```

## 개발자 공통 기본소양

```text
Git
Python
Algorithm
Computer Architecture
Operating Systems
Network
Database Systems
Security
```

## 웹 개발자

```text
42 Web Track
+ Database Systems
+ Security
+ Java
+ Backend Spring        # Java/Spring 사용 시
+ Distributed Services
+ Cloud Computing
```

## 게임 서버 개발자

```text
42 C++ / Network Track
+ Algorithm
+ Computer Architecture
+ Operating Systems
+ Security
+ Game Server
+ Distributed Services
+ Cloud Computing
```

---

# 8. Exercise 수행 원칙

모든 exercise에 동일한 규칙을 적용합니다.

```text
실제 프로젝트를 먼저 구현합니다.
→ 프로젝트 경험에서 어느 정도 시간이 지난 뒤 exercise를 시작합니다.
→ exercise의 README, 공개 API, 요구사항과 테스트만 확인합니다.
→ 가이드와 기존 구현을 보지 않고 직접 구현합니다.
→ 테스트가 실패하고 원인을 설명하지 못할 때만 관련 문서를 다시 읽습니다.
```

Exercise를 먼저 완료해야 실제 프로젝트를 시작할 수 있다고 판단하지 않습니다.

실제 프로젝트가 학습의 중심이고, 가이드는 프로젝트에 진입할 최소 지식을 제공하며, exercise는 시간이 지난 뒤 같은 능력을 다시 사용할 수 있는지 확인하기 위한 수단입니다.
