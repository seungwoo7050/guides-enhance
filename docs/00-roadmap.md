# Game Server 초기 학습 방향

1. 서버가 소유하는 authoritative state를 정의합니다.
2. fixed tick과 command 순서를 결정적으로 처리합니다.
3. connection과 session, room, match의 수명을 구분합니다.
4. snapshot과 delta를 이용한 replication을 살펴봅니다.
5. load와 trust 경계를 이후 단계에서 학습합니다.
