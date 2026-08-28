# ARP와 IPv6 Neighbor Discovery

호스트가 목적지 IP에 사용할 경로를 선택해도 Ethernet 프레임을 보내려면 현재 링크에서 사용할 목적지 MAC 주소가 필요합니다. IPv4는 ARP를 사용하고 IPv6는 ICMPv6 기반 Neighbor Discovery를 사용합니다. 둘 다 인터넷 전체에서 최종 목적지의 물리 주소를 찾는 프로토콜이 아니라 **현재 링크의 다음 홉**을 찾는 절차입니다.

## 학습 목표

- 목적지 IP와 이웃 조회 대상 IP를 구분합니다.
- ARP와 Neighbor Discovery의 요청·응답과 캐시 상태를 해석합니다.
- 경로 문제, 링크 문제와 이웃 주소 해석 실패를 구분합니다.

## 경로를 먼저 선택합니다

호스트 `192.0.2.10/24`가 다음 두 주소로 패킷을 보낸다고 가정합니다.

```text
192.0.2.50     → 직접 연결 경로 → 192.0.2.50의 MAC 조회
198.51.100.20  → 게이트웨이 경로 → 192.0.2.1의 MAC 조회
```

원격 서버의 MAC 주소는 첫 링크에서 필요하지 않습니다. 첫 라우터는 패킷을 받은 뒤 자신의 라우팅 테이블을 다시 조회하고, 다음 링크에서 사용할 이웃 주소를 따로 찾습니다.

따라서 이웃 문제를 조사하기 전에 `ip route get` 또는 이에 해당하는 명령으로 실제 다음 홉과 출력 인터페이스를 먼저 확인합니다.

## IPv4 ARP

ARP Request는 보통 Ethernet 브로드캐스트로 전송됩니다.

```text
Who has 192.0.2.1? Tell 192.0.2.10
192.0.2.1 is at 02:00:00:00:00:01
```

응답은 이웃 캐시에 저장됩니다. 운영체제는 항목을 단순히 있음과 없음으로만 관리하지 않고 `REACHABLE`, `STALE`, `DELAY`, `PROBE`, `FAILED` 같은 상태로 관리할 수 있습니다. 항목이 있다는 사실만으로 현재 통신이 성공한다고 보지 않습니다.

ARP 자체는 인증을 제공하지 않습니다. 같은 링크의 공격자가 거짓 응답을 보낼 수 있으므로 중요한 통신은 스위치 보호 기능, 네트워크 분리와 상위 암호화를 함께 사용합니다.

## Proxy ARP와 gratuitous ARP

Proxy ARP에서는 라우터나 중간 장비가 다른 호스트 대신 자신의 MAC 주소로 응답합니다. 송신 호스트는 목적지를 같은 링크에 있는 것처럼 처리하지만 실제 패킷은 중간 장비가 전달합니다.

Gratuitous ARP는 자신의 IP와 MAC 관계를 요청 없이 알리거나 중복 주소를 확인하고 캐시를 갱신할 때 사용합니다. 고가용성 장비의 활성 노드가 바뀐 뒤 새 MAC 위치를 알릴 때도 볼 수 있습니다.

요청과 일대일로 대응하지 않는 ARP Reply가 보였다는 이유만으로 공격으로 확정하지 않습니다. 배치 방식과 같은 시각의 다른 패킷을 함께 확인합니다.

## IPv6 Neighbor Discovery

IPv6는 ARP 대신 ICMPv6 Neighbor Discovery를 사용합니다.

- Neighbor Solicitation과 Neighbor Advertisement
- Router Solicitation과 Router Advertisement
- 프리픽스와 기본 라우터 발견
- 주소 자동 설정 정보
- Duplicate Address Detection
- 이웃 도달 가능성 확인과 redirect

IPv4 ARP의 링크 전체 브로드캐스트 대신 Solicited-Node Multicast를 사용합니다. IPv6에서 ICMPv6를 무차별 차단하면 이웃 주소 해석, 라우터 발견과 경로 MTU 탐색이 함께 깨질 수 있습니다.

Neighbor Discovery 메시지는 Hop Limit 255와 같은 조건을 확인해 링크 밖에서 들어온 일부 위조 메시지를 거부합니다. 그러나 같은 링크 안의 신뢰 문제가 사라지는 것은 아닙니다.

## 관찰 순서

Linux:

```sh
ip route get 192.0.2.50
ip neighbor show
ping -c 1 192.0.2.50
ip neighbor show
```

macOS:

```sh
route -n get 192.0.2.50
arp -an
ndp -an
```

실패를 조사할 때는 다음 순서를 사용합니다.

1. 목적지 IP에 선택된 경로와 다음 홉을 확인합니다.
2. 출력 인터페이스가 `UP` 상태이며 올바른 VLAN에 있는지 확인합니다.
3. 다음 홉의 이웃 항목 상태를 확인합니다.
4. ARP Request 또는 Neighbor Solicitation이 실제로 나가는지 캡처합니다.
5. Reply가 돌아오고 캐시 상태가 바뀌는지 확인합니다.
6. 주소 해석 뒤에도 실패하면 전달, 방화벽과 전송 단계를 확인합니다.

Reply가 없을 때는 목적지 호스트 중단, 잘못된 프리픽스, VLAN 분리, 스위치 포트 설정, 무선 클라이언트 격리나 중복 주소를 확인합니다. 캐시 삭제부터 시도하지 말고 현재 상태와 패킷을 먼저 보존합니다.

## 연결 프로젝트

[linux-routing-nat](../../exercises/linux-routing-nat/README.md)의 라우팅 실험에서 경로 제거 전후에 어떤 다음 홉을 찾게 되는지 예상하고 실제 결과와 비교합니다.

## 완료 기준

- 로컬 목적지와 원격 목적지에서 조회하는 다음 홉을 각각 계산합니다.
- 이웃 항목 상태와 요청·응답 캡처를 근거로 실패 지점을 좁힙니다.
- ARP와 Neighbor Discovery의 공통 목적과 서로 다른 메시지 형식을 설명합니다.
