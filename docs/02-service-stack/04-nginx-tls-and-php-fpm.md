# Nginx, TLS와 PHP-FPM

이 장에서는 외부의 HTTPS 요청을 Nginx가 받고, PHP로 처리해야 하는 요청을 PHP-FPM에 FastCGI로 전달하는 구성을 설명합니다. 핵심은 설정 지시어를 개별적으로 외우는 것이 아니라 **각 구간에서 어떤 프로토콜을 사용하고, 어느 프로세스가 어떤 파일 경로를 해석하는지** 추적하는 것입니다.

```text
클라이언트
    │ HTTPS = HTTP over TLS
    ▼
Nginx :443
    │ FastCGI
    ▼
PHP-FPM :9000
    │ SCRIPT_FILENAME
    ▼
/var/www/html/index.php
```

한 요청을 진단할 때는 다음 세 경계를 구분해야 합니다.

```text
클라이언트 ↔ Nginx      : TCP + TLS + HTTP
Nginx ↔ PHP-FPM         : FastCGI
PHP-FPM ↔ PHP 파일      : 컨테이너 내부 파일 시스템 경로
```

이 세 경계 중 하나만 잘못되어도 요청은 실패할 수 있습니다. 예를 들어 Nginx와 PHP-FPM 사이의 TCP 연결이 성공하더라도 `SCRIPT_FILENAME`이 PHP-FPM 컨테이너의 실제 파일 경로와 다르면 PHP 코드는 실행되지 않습니다.

## 1. 각 프로세스가 담당하는 일

### Nginx

Nginx는 외부 요청을 받아 어디에서 처리할지 결정하는 프런트 서버 역할을 합니다.

- 외부 TCP 연결을 받습니다.
- HTTPS 연결에서는 TLS 핸드셰이크와 암호화를 처리합니다.
- HTTP 요청의 메서드, URI와 헤더를 읽습니다.
- 정적 파일을 직접 반환할 수 있습니다.
- `server`와 `location` 설정에 따라 요청 처리 방법을 선택합니다.
- PHP로 처리해야 하는 요청을 FastCGI 형식으로 PHP-FPM에 전달합니다.

Nginx 자체가 PHP 소스 코드를 해석하거나 실행하는 것은 아닙니다.

### PHP-FPM

PHP-FPM(FastCGI Process Manager)은 PHP 실행 프로세스를 관리하는 FastCGI 서버입니다.

- PHP 작업 프로세스(worker)를 유지하거나 필요할 때 생성합니다.
- Nginx가 보낸 FastCGI 요청을 받습니다.
- `SCRIPT_FILENAME` 등의 FastCGI 파라미터를 사용해 실행할 PHP 파일을 결정합니다.
- PHP 코드를 실행합니다.
- 실행 결과의 상태, 헤더와 본문을 FastCGI 응답으로 Nginx에 반환합니다.

PHP-FPM의 TCP 포트가 열려 있어도 일반적인 HTTP 서버가 되는 것은 아닙니다. 따라서 브라우저나 `curl`이 PHP-FPM 포트에 직접 HTTP 요청을 보내는 구조로 사용하지 않습니다.

### PHP 애플리케이션

실제 비즈니스 로직은 PHP 코드가 담당합니다.

- 요청 메서드, URI, 쿼리 문자열과 본문을 읽습니다.
- 입력을 검증합니다.
- 필요한 경우 데이터베이스를 조회하거나 변경합니다.
- 응답 상태 코드, 헤더와 본문을 만듭니다.

전체 흐름은 다음처럼 생각할 수 있습니다.

```text
Nginx: 이 요청을 누가 처리할 것인가?
PHP-FPM: 어느 PHP 프로세스가 어느 스크립트를 실행할 것인가?
PHP 코드: 요청에 대해 어떤 응답을 만들 것인가?
```

## 2. 외부에는 Nginx만 공개합니다

Compose에서는 일반적으로 Nginx의 HTTPS 포트만 호스트에 게시하고 PHP-FPM은 내부 네트워크에서만 접근하게 합니다.

```yaml
services:
  gateway:
    ports:
      - "127.0.0.1:19443:443"
    networks:
      - app-net

  app:
    networks:
      - app-net

networks:
  app-net:
```

여기서 `127.0.0.1:19443:443`은 다음 의미입니다.

```text
호스트 127.0.0.1:19443
        │
        ▼
gateway 컨테이너 :443
```

반면 PHP-FPM의 `9000`번 포트는 호스트에 게시하지 않아도 됩니다. `gateway`와 `app`이 같은 Compose 네트워크에 연결되어 있으면 Nginx는 서비스 이름을 사용해 다음 주소로 연결할 수 있습니다.

```text
app:9000
```

Compose의 서비스 이름 `app`은 같은 네트워크 안에서 DNS 이름처럼 사용됩니다. 따라서 이 구성이 동작하려면 **Nginx와 PHP-FPM 컨테이너가 실제로 하나 이상의 같은 네트워크를 공유해야 합니다.**

호스트 포트 게시와 컨테이너 간 통신은 구분해야 합니다.

```text
클라이언트 → gateway    : 게시된 호스트 포트 사용
 gateway → app          : Compose 내부 네트워크와 컨테이너 포트 사용
```

이 구조의 장점은 다음과 같습니다.

- 외부 진입점과 TLS 인증서 관리를 Nginx에 모을 수 있습니다.
- PHP-FPM을 외부에서 직접 접근할 필요가 없습니다.
- Nginx와 PHP 작업 프로세스의 자원 설정을 독립적으로 조정할 수 있습니다.

## 3. Nginx 설정의 기본 단위

Nginx HTTP 설정은 문맥(context)별 블록으로 구성됩니다.

```nginx
http {
    server {
        listen 443 ssl;

        location / {
            # 이 URI 범위의 요청 처리
        }
    }
}
```

각 문맥의 역할은 다음과 같습니다.

- `http`: 여러 HTTP 가상 서버에 공통으로 적용되는 설정을 둡니다.
- `server`: 특정 주소와 포트에서 요청을 받을 가상 서버를 정의합니다.
- `location`: 선택된 `server` 안에서 요청 URI에 맞는 처리 규칙을 정의합니다.

요청은 대략 다음 순서로 처리됩니다.

```text
수신 주소/포트
→ server 선택
→ location 선택
→ 정적 파일 반환 또는 FastCGI 전달 등의 처리
```

공식 Nginx 이미지의 기본 `nginx.conf`는 일반적으로 `/etc/nginx/conf.d/*.conf`를 `http` 문맥 안에서 포함합니다. 따라서 프로젝트에서 `/etc/nginx/conf.d/default.conf` 같은 파일을 교체한다면 보통 그 파일에는 `http { ... }`가 아니라 `server { ... }` 블록을 둡니다.

설정을 적용하기 전에 문법과 참조 파일을 검사합니다.

실행 중인 컨테이너라면:

```sh
docker compose exec gateway nginx -t
```

설정 오류 때문에 컨테이너가 시작하지 못하는 상황이라면 서비스 구성을 이용해 일회성 컨테이너에서 검사할 수도 있습니다.

```sh
docker compose run --rm --no-deps gateway nginx -t
```

`nginx -t`는 문법뿐 아니라 인증서 같은 설정에서 참조한 파일을 읽을 수 있는지도 함께 검사하므로 시작 실패를 진단할 때 중요합니다.

## 4. `listen`, `server_name`과 HTTP/2

최근 Nginx에서는 다음과 같이 TLS 수신과 HTTP/2 활성화를 분리해서 표현할 수 있습니다.

```nginx
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;

    http2 on;
    server_name _;
}
```

### `listen`

`listen`은 Nginx가 어느 주소와 포트에서 연결을 받을지 정의합니다.

```nginx
listen 443 ssl;
```

은 IPv4 기본 주소의 443번 포트에서 TLS 연결을 받겠다는 의미이고,

```nginx
listen [::]:443 ssl;
```

은 IPv6 수신 소켓을 정의합니다. 실제 IPv4/IPv6 동작은 운영체제의 소켓 설정에도 영향을 받을 수 있으므로 두 주소 계열을 명시적으로 둘 다 설정하는 구성이 흔합니다.

### `default_server`

같은 주소와 포트를 사용하는 `server` 블록이 여러 개 있을 때 요청의 서버 이름이 어떤 블록에도 맞지 않으면 해당 수신 소켓의 `default_server`가 사용됩니다.

중요한 점은 **기본 서버 여부는 `server_name`이 아니라 `listen ... default_server`가 결정한다는 것**입니다.

### `server_name _`

`server_name`은 요청의 서버 이름과 비교할 이름을 정의합니다.

```nginx
server_name example.com www.example.com;
```

처럼 실제 호스트 이름을 지정할 수 있습니다.

예제에서 자주 쓰는

```nginx
server_name _;
```

의 `_`에는 특별한 "모든 호스트와 일치" 의미가 없습니다. 실제 도메인과 충돌하기 어려운 이름을 관례적으로 적은 것입니다. 모든 미일치 요청을 받게 만드는 역할은 앞에서 본 `default_server`가 담당합니다.

### HTTP/2 문법과 버전

`http2 on;` 지시어는 Nginx 1.25.1에서 추가되었습니다.

```nginx
listen 443 ssl;
http2 on;
```

더 오래된 버전에서는 다음 문법이 사용되었습니다.

```nginx
listen 443 ssl http2;
```

현재 문서에서는 `listen`의 `http2` 파라미터가 deprecated로 표시되어 있으므로 새 버전에서는 `http2 on;`을 사용하는 편이 명확합니다. 반대로 오래된 이미지에서는 `http2 on;` 자체를 알지 못할 수 있습니다.

따라서 다른 프로젝트나 이미지에서 설정을 옮길 때는 먼저 실제 버전을 확인합니다.

```sh
nginx -v
nginx -t
```

## 5. 정적 파일과 동적 요청

### 정적 파일은 Nginx가 직접 반환할 수 있습니다

```nginx
location = /static.txt {
    root /usr/share/nginx/html;
    default_type text/plain;
}
```

`location = /static.txt`의 `=`는 URI가 정확히 `/static.txt`인 요청만 이 블록에 일치시키겠다는 의미입니다.

이 경우 `root`를 기준으로 실제 파일은 다음과 같이 결정됩니다.

```text
root: /usr/share/nginx/html
URI : /static.txt
파일: /usr/share/nginx/html/static.txt
```

### PHP 요청은 FastCGI로 전달합니다

다음 예제는 모든 `/` 이하 요청을 하나의 프런트 컨트롤러 `index.php`로 보내는 구성을 가정합니다.

```nginx
location / {
    include fastcgi_params;

    fastcgi_param SCRIPT_FILENAME /var/www/html/index.php;
    fastcgi_param SCRIPT_NAME /index.php;
    fastcgi_param PATH_INFO $uri;
    fastcgi_param REQUEST_URI $request_uri;
    fastcgi_param HTTPS on;

    fastcgi_pass app:9000;
}
```

여기서 중요한 것은 **클라이언트의 URI와 실제 실행되는 PHP 파일이 반드시 같은 문자열일 필요는 없다는 것**입니다.

예를 들어 클라이언트가 다음 요청을 보냈다고 가정합니다.

```text
GET /users/42?view=full
```

위와 같은 프런트 컨트롤러 구성에서는 대략 다음 정보가 PHP-FPM에 전달됩니다.

```text
SCRIPT_FILENAME = /var/www/html/index.php
SCRIPT_NAME     = /index.php
PATH_INFO       = /users/42
REQUEST_URI     = /users/42?view=full
```

즉 실제로 실행하는 파일은 항상 `index.php`이고, 애플리케이션은 원래 요청 URI를 이용해 내부 라우팅을 수행합니다.

이 예시는 **모든 요청을 `index.php`로 보내는 애플리케이션 구조**를 위한 것입니다. 요청된 `.php` 파일을 각각 직접 실행하는 일반적인 PHP 사이트라면 `SCRIPT_FILENAME`을 `$document_root$fastcgi_script_name`처럼 요청 URI에 따라 계산하는 다른 구성이 필요합니다.

### `include fastcgi_params`

FastCGI 서버가 HTTP 요청 정보를 이해하려면 요청 메서드, 쿼리 문자열, 콘텐츠 길이 등 여러 값을 FastCGI 파라미터로 전달해야 합니다.

```nginx
include fastcgi_params;
```

은 배포판이나 이미지에 포함된 기본 FastCGI 파라미터 묶음을 읽어옵니다. 프로젝트에서 필요한 `SCRIPT_FILENAME`, `HTTPS` 같은 값을 추가로 명시할 수 있습니다.

실제 포함 파일의 내용은 사용 중인 이미지에서 확인할 수 있습니다.

```sh
cat /etc/nginx/fastcgi_params
```

### `fastcgi_pass`

```nginx
fastcgi_pass app:9000;
```

은 FastCGI 요청을 보낼 **서버 주소**를 지정합니다.

```text
app   : Compose 내부 DNS로 찾을 서비스 이름
9000  : PHP-FPM이 FastCGI 요청을 듣는 포트
```

`fastcgi_pass`가 올바르려면 다음 조건이 모두 맞아야 합니다.

```text
gateway와 app이 같은 네트워크에 있음
→ gateway에서 app 이름을 해석할 수 있음
→ app 컨테이너에서 PHP-FPM이 9000번 포트를 수신 중임
→ 네트워크 정책이 연결을 막지 않음
```

### `SCRIPT_FILENAME`

```nginx
fastcgi_param SCRIPT_FILENAME /var/www/html/index.php;
```

은 PHP-FPM에 **실제로 실행할 PHP 스크립트의 파일 시스템 경로**를 전달합니다.

이 경로는 Nginx 컨테이너가 아니라 **PHP-FPM 프로세스가 실행되는 컨테이너에서 해석됩니다.**

```text
Nginx가 전달하는 값
/var/www/html/index.php
        │
        ▼
app 컨테이너 안에서 이 파일이 실제로 존재해야 함
```

따라서 두 컨테이너의 디렉터리 구조가 다르더라도 문제가 되지 않습니다. 중요한 것은 `SCRIPT_FILENAME`의 값이 PHP-FPM 쪽 실제 경로와 일치하는가입니다.

FastCGI 연결 자체가 성공해도 이 값이 잘못되면 PHP-FPM 로그에 `Primary script unknown`이나 스크립트 파일을 찾을 수 없다는 오류가 나타날 수 있습니다.

### `$uri`와 `$request_uri`

두 변수는 비슷해 보이지만 용도가 다릅니다.

- `$request_uri`: 클라이언트가 보낸 원래 URI를 쿼리 문자열까지 포함해 보존합니다.
- `$uri`: Nginx가 처리 중인 정규화된 URI이며 내부 리다이렉트 등에 따라 값이 바뀔 수 있습니다. 쿼리 문자열은 포함하지 않습니다.

따라서 애플리케이션에 원래 요청 주소를 전달해야 할 때는 보통 `REQUEST_URI $request_uri`를 사용합니다.

### `HTTPS on`

클라이언트와 Nginx 사이에서는 HTTPS를 사용하지만 Nginx와 PHP-FPM 사이에서는 TLS가 아니라 FastCGI를 사용합니다.

```text
클라이언트 ──HTTPS──> Nginx ──FastCGI──> PHP-FPM
```

따라서 PHP-FPM이 연결 자체만 보고 원래 요청이 HTTPS였는지 알아낼 수는 없습니다. 애플리케이션이 이 정보를 필요로 한다면 Nginx가 FastCGI 파라미터로 전달해야 합니다.

고정 HTTPS 서버라면 다음처럼 명시할 수 있습니다.

```nginx
fastcgi_param HTTPS on;
```

HTTP와 HTTPS를 모두 처리하는 공통 설정에서는 Nginx의 `$https` 변수를 사용하는 방식도 있습니다.

```nginx
fastcgi_param HTTPS $https if_not_empty;
```

## 6. TLS 인증서와 개인키

Nginx가 HTTPS 연결을 받으려면 최소한 인증서와 그 인증서에 대응하는 개인키가 필요합니다.

```nginx
ssl_certificate /etc/nginx/tls/development.crt;
ssl_certificate_key /etc/nginx/tls/development.key;
ssl_protocols TLSv1.2 TLSv1.3;
```

역할을 구분하면 다음과 같습니다.

- **개인키(private key)**: 서버가 비밀로 보관해야 하는 키입니다.
- **인증서(certificate)**: 서버의 공개키와 주체 정보, 유효기간, 발급자, 확장 정보(SAN 등)를 서명된 형태로 담습니다.
- **인증서 체인(chain)**: 클라이언트가 서버 인증서를 신뢰 가능한 루트 CA까지 검증할 수 있도록 중간 인증서를 연결합니다.

개인키는 클라이언트에게 전송하지 않습니다. 반면 인증서와 필요한 체인은 TLS 핸드셰이크 과정에서 클라이언트가 검증할 수 있도록 제공됩니다.

인증서와 개인키가 서로 대응하지 않거나 Nginx 프로세스가 파일을 읽을 수 없으면 TLS 설정을 정상적으로 로드할 수 없습니다. 이 경우 `nginx -t`와 시작 로그를 먼저 확인합니다.

### 로컬 개발용 자체 서명 인증서

로컬에서 TLS 요청 경로를 연습하려면 자체 서명 인증서를 만들 수 있습니다.

```sh
openssl req -x509 -newkey rsa:2048 -nodes \
  -days 30 \
  -subj '/CN=localhost' \
  -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' \
  -keyout development.key \
  -out development.crt
```

주요 옵션의 의미는 다음과 같습니다.

- `-x509`: 인증서 서명 요청(CSR) 대신 자체 서명 X.509 인증서를 출력합니다.
- `-newkey rsa:2048`: 새 RSA 개인키를 생성합니다.
- `-nodes`: 생성한 개인키를 암호로 보호하지 않습니다. 자동 시작 서버가 암호 입력 없이 키를 읽어야 하는 개발 환경에서 편리하지만 키 파일 보호가 더 중요해집니다.
- `-days 30`: 자체 서명 인증서의 유효기간을 30일로 지정합니다.
- `-subj`: 인증서 주체(subject)를 지정합니다.
- `-addext subjectAltName=...`: 인증서가 유효한 DNS 이름과 IP 주소를 SAN 확장에 기록합니다.

개인키 파일은 불필요한 사용자에게 읽기 권한을 주지 않습니다.

```sh
chmod 600 development.key
```

다만 컨테이너가 root가 아닌 사용자로 Nginx를 실행한다면 단순히 `600`으로 만드는 것만으로 충분하지 않을 수 있습니다. **Nginx가 실제로 키를 읽어야 하는 사용자에게는 읽기 권한이 있고 다른 사용자에게는 노출되지 않도록 소유자와 마운트 권한까지 함께 확인해야 합니다.**

### 자체 서명 인증서와 신뢰

자체 서명 인증서도 TLS 암호화 자체는 사용할 수 있습니다. 그러나 일반적인 클라이언트의 신뢰 저장소에는 해당 인증서를 서명한 CA가 없기 때문에 서버 신원 검증은 실패합니다.

따라서 다음 명령은 개발 중 연결 경로를 확인하는 용도일 뿐입니다.

```sh
curl -k https://127.0.0.1:19443/
```

`-k` 또는 `--insecure`는 인증서 검증 실패를 무시합니다. 즉 이 명령이 성공했다고 해서 운영 환경에서 인증서 체인, 호스트 이름, 유효기간 검증이 올바르다는 뜻은 아닙니다.

자체 서명 인증서 자체를 명시적으로 신뢰해 검증하고 싶다면 예를 들어 다음처럼 CA 파일로 지정할 수 있습니다.

```sh
curl --cacert development.crt https://localhost:19443/
```

운영 서비스에서는 일반적으로 클라이언트가 신뢰할 수 있는 CA가 발급한 인증서 체인과 자동 갱신 절차를 사용합니다.

## 7. PHP-FPM의 프로세스 구성

PHP-FPM은 하나의 마스터 프로세스가 풀(pool)의 작업 프로세스를 관리하는 구조로 실행됩니다.

```text
php-fpm master (PID 1)
├─ worker
├─ worker
└─ worker
```

컨테이너에서는 일반적으로 PHP-FPM 마스터가 포그라운드에서 실행되어 컨테이너의 주 프로세스가 되게 합니다.

```dockerfile
CMD ["php-fpm", "-F"]
```

프로세스를 데몬으로 백그라운드화해 버리면 컨테이너 런타임이 주 프로세스의 종료 상태와 신호를 정상적으로 관리하기 어려워집니다.

예시 풀 설정은 다음과 같습니다.

```ini
[www]
user = www-data
group = www-data
listen = 9000

pm = dynamic
pm.max_children = 8
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3

ping.path = /ping
ping.response = pong
```

### `listen`

```ini
listen = 9000
```

은 이 풀에서 FastCGI 요청을 받을 주소를 정의합니다. PHP-FPM은 TCP 주소/포트뿐 아니라 Unix 도메인 소켓을 사용할 수도 있습니다.

컨테이너를 분리해 Nginx와 PHP-FPM이 서로 다른 컨테이너에서 실행되는 구성에서는 Unix 소켓을 공유하도록 별도 볼륨을 구성하지 않는 한 TCP `app:9000` 방식이 단순합니다.

### `pm = dynamic`

PHP-FPM의 프로세스 관리 방식에는 대표적으로 `static`, `dynamic`, `ondemand`가 있습니다.

- `static`: `pm.max_children`만큼의 작업 프로세스를 고정적으로 유지합니다.
- `dynamic`: 유휴 프로세스 수를 보면서 작업 프로세스를 늘리거나 줄입니다.
- `ondemand`: 요청이 들어올 때 필요에 따라 작업 프로세스를 생성합니다.

`dynamic`에서는 다음 값들이 함께 작동합니다.

```ini
pm.max_children = 8
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
```

- `pm.start_servers`: FPM 시작 시 생성할 작업 프로세스 수
- `pm.min_spare_servers`: 유지하려는 최소 유휴 작업 프로세스 수
- `pm.max_spare_servers`: 유지하려는 최대 유휴 작업 프로세스 수
- `pm.max_children`: 동시에 존재할 수 있는 작업 프로세스 수의 상한

### `pm.max_children`

하나의 FPM 작업 프로세스는 한 시점에 하나의 요청을 처리하므로 `pm.max_children`은 이 풀에서 동시에 처리할 수 있는 요청 수의 상한과 직접 연결됩니다.

하지만 값을 크게 만든다고 처리량이 무조건 증가하지는 않습니다. 각 작업 프로세스가 메모리를 사용하기 때문입니다.

예를 들어 작업 프로세스 하나가 실제 부하에서 평균 80 MiB 정도를 사용하고 `pm.max_children = 20`이라면 작업 프로세스만으로도 단순 계산상 약 1.6 GiB까지 필요할 수 있습니다.

```text
80 MiB × 20 ≈ 1600 MiB
```

여기에 FPM 마스터, OPcache, 운영체제, 다른 프로세스와 순간적인 메모리 증가분도 필요합니다. 메모리를 초과하면 스와핑이나 OOM 종료가 발생해 오히려 지연과 장애가 커질 수 있습니다.

따라서 `pm.max_children`은 다음을 측정해 조정합니다.

- 실제 PHP 작업 프로세스의 메모리 사용량
- 요청 처리 시간
- 동시 요청 수
- 컨테이너 또는 호스트의 메모리 한도
- CPU와 데이터베이스 등 다른 병목

## 8. 상태 검사 범위를 나눕니다

상태 검사는 "무엇까지 정상임을 증명하는가"를 먼저 정해야 합니다. 하나의 헬스 체크가 모든 구성 요소의 상태를 동시에 표현하게 만들면 장애 원인을 구분하기 어려워집니다.

### Nginx와 TLS만 확인

```nginx
location = /healthz {
    access_log off;
    default_type text/plain;
    return 200 "ok\n";
}
```

호스트에서 다음처럼 검사할 수 있습니다.

```sh
curl -kfsS https://127.0.0.1:19443/healthz
```

이 검사가 성공하면 최소한 다음 경로는 동작합니다.

```text
호스트 포트
→ TCP 연결
→ TLS 연결
→ Nginx
→ /healthz 응답
```

하지만 PHP-FPM과 데이터베이스를 거치지 않으므로 그 둘의 정상 여부는 증명하지 않습니다.

### PHP-FPM 자체 확인

FPM 설정에 다음이 있다면:

```ini
ping.path = /ping
ping.response = pong
```

FPM의 FastCGI ping 엔드포인트를 사용할 수 있습니다.

`cgi-fcgi`가 설치되어 있다는 전제에서 **PHP-FPM과 같은 컨테이너 내부**에서 다음처럼 확인할 수 있습니다.

```sh
REQUEST_METHOD=GET \
SCRIPT_NAME=/ping \
SCRIPT_FILENAME=/ping \
cgi-fcgi -bind -connect 127.0.0.1:9000 | grep -q pong
```

여기서 `127.0.0.1:9000`은 명령을 `app` 컨테이너 안에서 실행한다는 전제입니다.

```sh
docker compose exec app sh
```

같은 방식으로 컨테이너 셸에 들어간 뒤 검사할 수 있습니다.

`gateway` 컨테이너에서 검사한다면 `127.0.0.1`은 gateway 자신을 가리키므로 올바르지 않습니다. 이 경우 같은 Compose 네트워크의 서비스 이름을 사용해야 합니다.

```text
app:9000
```

또한 PHP-FPM은 HTTP 서버가 아니므로 다음 검사는 프로토콜이 맞지 않습니다.

```sh
curl http://127.0.0.1:9000
```

TCP 포트가 열려 있는지 확인하는 검사와 FPM이 올바른 FastCGI 응답을 만드는지 확인하는 검사는 구분해야 합니다.

### 전체 요청 경로 확인

애플리케이션이 `/health` 요청에서 PHP 코드와 데이터베이스까지 확인하도록 구현되어 있다면 다음 요청은 더 깊은 경로를 검사합니다.

```sh
curl -kfsS https://127.0.0.1:19443/health
```

```text
클라이언트
→ TLS
→ Nginx
→ FastCGI
→ PHP-FPM
→ PHP 애플리케이션
→ 데이터베이스
→ 응답
```

따라서 `/healthz`와 `/health`는 서로 다른 질문에 답합니다.

```text
/healthz : Nginx 진입점이 살아 있는가?
/health  : 애플리케이션의 주요 의존성까지 요청을 처리할 수 있는가?
```

`/healthz`가 200을 반환해도 PHP-FPM이 죽어 있다면 `/health`는 실패할 수 있습니다.

## 9. 오류를 계층별로 나누어 확인하기

HTTP 상태 코드만 보고 오류 발생 지점을 단정하면 안 됩니다. 같은 404나 500도 Nginx가 만들 수도 있고 PHP 애플리케이션이 만들 수도 있습니다. **상태 코드와 함께 Nginx access/error log, PHP-FPM 로그, 애플리케이션 로그를 확인해야 합니다.**

### 연결 자체가 거부됨

예:

```text
Connection refused
```

클라이언트가 Nginx까지 도달하지 못한 상태일 수 있습니다.

확인 순서:

```text
Compose 컨테이너 실행 상태
→ 호스트 포트 게시 여부
→ Nginx 프로세스 실행 여부
→ Nginx의 실제 listen 포트
```

```sh
docker compose ps -a
docker compose logs gateway
```

### TLS 핸드셰이크 또는 인증서 검증 오류

TLS 연결 단계에서 실패한다면 다음을 확인합니다.

- 인증서의 SAN에 접속 호스트 이름 또는 IP가 포함되어 있는가
- 인증서가 만료되지 않았는가
- 필요한 인증서 체인이 제공되는가
- 인증서와 개인키가 서로 대응하는가
- 클라이언트가 발급자를 신뢰하는가

서버가 제공하는 인증서를 직접 살펴볼 수 있습니다.

```sh
openssl s_client \
  -connect 127.0.0.1:19443 \
  -servername localhost \
  </dev/null
```

`-servername localhost`는 TLS SNI(Server Name Indication)에 사용할 이름입니다. 여러 TLS `server` 블록이 같은 주소에서 동작할 때 어떤 인증서를 선택하는지 확인하는 데 특히 중요합니다.

### 404 Not Found

404는 "요청 경로에 해당하는 리소스를 찾지 못했다"는 결과지만 **누가 404를 만들었는지는 별도로 확인해야 합니다.**

Nginx가 만든 404라면 다음을 확인합니다.

```text
server 선택
→ location 선택
→ root/alias 경로
→ 정적 파일 존재 여부
```

PHP 애플리케이션이 만든 404라면 FastCGI 전달은 성공했고 애플리케이션 라우팅에서 해당 경로를 찾지 못했을 수 있습니다.

### 403 Forbidden

정적 파일 요청에서 Nginx가 403을 반환한다면 Nginx worker가 파일이나 상위 디렉터리를 읽거나 탐색하지 못하는 권한 문제를 확인합니다.

```text
Nginx worker 사용자
→ 상위 디렉터리의 실행(x) 권한
→ 파일의 읽기(r) 권한
```

하지만 애플리케이션의 인증/인가 로직도 403을 반환할 수 있으므로 로그를 통해 응답 생성 주체를 구분합니다.

### 502 Bad Gateway

Nginx가 upstream인 PHP-FPM과 정상적인 FastCGI 통신을 완료하지 못하면 502가 나타날 수 있습니다.

다음 순서로 계층을 하나씩 확인합니다.

```text
app 컨테이너가 실행 중인가?
→ php-fpm 프로세스가 실행 중인가?
→ php-fpm이 예상 주소/포트에서 listen 중인가?
→ gateway와 app이 같은 네트워크에 있는가?
→ gateway에서 app 이름이 해석되는가?
→ gateway에서 app:9000으로 연결할 수 있는가?
→ FastCGI 파라미터가 올바른가?
→ SCRIPT_FILENAME이 app 컨테이너의 실제 파일 경로와 맞는가?
```

대표적인 원인은 다음과 같습니다.

- PHP-FPM 프로세스가 종료됨
- `fastcgi_pass`의 서비스 이름 또는 포트가 잘못됨
- 두 컨테이너가 같은 네트워크에 없음
- PHP-FPM이 예상과 다른 주소에만 바인딩됨
- upstream이 연결을 끊거나 유효하지 않은 FastCGI 응답을 반환함

`SCRIPT_FILENAME` 오류는 FPM의 응답 형태와 설정에 따라 404/502 등으로 관찰될 수 있으므로 Nginx와 FPM 로그를 함께 확인하는 것이 안전합니다.

### 500 Internal Server Error

FastCGI 통신과 PHP 실행 단계까지 도달한 뒤 PHP 코드에서 예외나 치명적 오류가 발생하면 500이 반환될 수 있습니다.

확인할 곳은 다음과 같습니다.

```text
PHP-FPM 로그
→ worker stderr 수집 설정
→ 애플리케이션 로그
→ 예외/에러 메시지
```

단, 500 역시 Nginx 자체 설정이나 내부 처리에서 생성될 가능성이 있으므로 상태 코드만으로 "PHP 코드 오류"라고 단정하지 않습니다.

## 10. 자주 생기는 오해

### "PHP-FPM 포트에 `curl`을 보내면 상태를 확인할 수 있습니다"

그렇지 않습니다. `curl`은 HTTP 클라이언트이고 PHP-FPM은 FastCGI 서버입니다.

```text
curl       → HTTP를 말함
PHP-FPM    → FastCGI를 기대함
```

FPM 자체를 검사하려면 `cgi-fcgi`처럼 FastCGI 요청을 만들 수 있는 도구를 사용하거나, Nginx를 통해 FPM ping 경로를 노출하는 별도 구성을 사용해야 합니다.

### "자체 서명 인증서도 암호화되므로 운영에서 충분히 안전합니다"

TLS 암호화와 서버 신원 신뢰는 같은 개념이 아닙니다.

```text
암호화: 통신 내용을 보호하는가?
인증  : 접속한 서버가 기대한 서버임을 신뢰할 수 있는가?
```

자체 서명 인증서는 별도의 신뢰 배포 없이 일반 공개 서비스의 서버 신원을 증명하지 못합니다.

### "`curl -k`가 성공하면 TLS 설정이 올바릅니다"

`-k`는 인증서 검증을 비활성화합니다. 따라서 TCP/TLS 연결과 HTTP 응답 경로를 시험하는 데는 유용하지만 다음 항목이 올바름을 증명하지 않습니다.

- 인증서 체인의 신뢰성
- 호스트 이름 일치
- 신뢰 가능한 CA 발급 여부

운영 검증에서는 `-k` 없이 실제 신뢰 체인을 통과해야 합니다.

### "502는 PHP 코드 오류입니다"

502는 우선 Nginx와 upstream 사이의 문제로 해석해야 합니다.

```text
Nginx
→ 이름 해석
→ 네트워크
→ PHP-FPM listen 주소/포트
→ FastCGI 통신
→ 스크립트 경로
```

PHP 코드가 정상적으로 시작되어 애플리케이션 내부에서 오류 응답 500을 만들었다면 클라이언트는 일반적으로 500을 받습니다. 따라서 502가 보이면 PHP 코드 내부 로직부터 보기보다 Nginx와 FPM의 경계를 먼저 확인하는 것이 효율적입니다.

### "`server_name _;`가 모든 호스트 이름을 의미합니다"

아닙니다. `_`는 특별한 와일드카드가 아닙니다. 일치하지 않는 요청을 처리할 기본 가상 서버는 다음 설정이 정합니다.

```nginx
listen 443 ssl default_server;
```

## 확인 문제

1. 클라이언트와 Nginx 사이, Nginx와 PHP-FPM 사이에서는 각각 어떤 프로토콜을 사용합니까?
2. PHP-FPM의 9000번 포트를 호스트에 게시할 필요가 없는 이유는 무엇입니까?
3. `gateway`에서 `fastcgi_pass app:9000;`을 사용하려면 Compose 네트워크에 어떤 조건이 필요합니까?
4. `fastcgi_pass`와 `SCRIPT_FILENAME`은 각각 무엇을 지정합니까?
5. 클라이언트가 `/users/42`를 요청해도 `SCRIPT_FILENAME`이 `/var/www/html/index.php`일 수 있는 이유는 무엇입니까?
6. `server_name _;`와 `listen ... default_server`의 역할은 어떻게 다릅니까?
7. `http2 on;`을 다른 Nginx 이미지로 옮길 때 버전을 확인해야 하는 이유는 무엇입니까?
8. `/healthz`가 성공해도 `/health`가 502가 될 수 있는 이유는 무엇입니까?
9. `cgi-fcgi -connect 127.0.0.1:9000` 검사를 gateway 컨테이너에서 실행하면 잘못된 이유는 무엇입니까?
10. `pm.max_children`을 지나치게 크게 설정하면 어떤 문제가 생길 수 있습니까?
11. HTTP 404나 500만 보고 오류가 Nginx와 PHP 중 어디에서 발생했는지 단정할 수 없는 이유는 무엇입니까?
12. `curl -k`의 성공이 운영 TLS 인증서 검증의 증거가 될 수 없는 이유는 무엇입니까?

## 참고 문서

- Nginx 요청 처리: https://nginx.org/en/docs/http/request_processing.html
- Nginx 서버 이름: https://nginx.org/en/docs/http/server_names.html
- Nginx HTTP/2: https://nginx.org/en/docs/http/ngx_http_v2_module.html
- Nginx FastCGI: https://nginx.org/en/docs/http/ngx_http_fastcgi_module.html
- Nginx TLS: https://nginx.org/en/docs/http/ngx_http_ssl_module.html
- PHP-FPM 설정: https://www.php.net/manual/en/install.fpm.configuration.php
- Docker Compose 네트워킹: https://docs.docker.com/compose/how-tos/networking/
- OpenSSL `req`: https://docs.openssl.org/master/man1/openssl-req/
