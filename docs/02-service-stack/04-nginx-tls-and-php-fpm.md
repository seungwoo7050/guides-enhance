# Nginx, TLS와 PHP-FPM

이 장에서는 외부 HTTPS 요청을 Nginx가 받고, PHP 요청을 PHP-FPM으로 전달하는 구성을 설명합니다. 핵심은 설정 지시어를 외우는 것이 아니라 요청이 어느 프로토콜과 파일 경로를 거치는지 추적하는 것입니다.

```text
클라이언트
    │ HTTPS
    ▼
Nginx :443
    │ FastCGI
    ▼
PHP-FPM :9000
    │
    ▼
/var/www/html/index.php
```

## 1. 각 프로세스가 담당하는 일

### Nginx

- 외부 TCP 연결과 HTTP(S) 요청을 받습니다.
- TLS 핸드셰이크를 처리합니다.
- 정적 파일을 직접 반환합니다.
- 요청 경로에 따라 처리 방법을 고릅니다.
- 동적 요청을 PHP-FPM에 FastCGI로 전달합니다.

### PHP-FPM

- PHP 작업 프로세스를 미리 유지합니다.
- FastCGI 요청을 받습니다.
- 지정된 PHP 파일을 실행합니다.
- 실행 결과를 Nginx에 반환합니다.

### PHP 애플리케이션

- 요청 메서드, 경로와 본문을 읽습니다.
- 입력을 검증합니다.
- 데이터베이스를 조회하거나 변경합니다.
- 응답 상태, 헤더와 본문을 만듭니다.

Nginx는 PHP 코드를 직접 실행하지 않습니다. PHP-FPM은 브라우저가 직접 접속하는 HTTP 서버가 아닙니다.

## 2. 외부에는 Nginx만 공개합니다

Compose에서는 Nginx의 HTTPS 포트만 호스트에 게시합니다.

```yaml
services:
  gateway:
    ports:
      - "127.0.0.1:19443:443"

  app:
    networks:
      - app-net
```

PHP-FPM의 9000번 포트는 같은 내부 네트워크의 Nginx만 사용합니다. 호스트에 게시할 필요가 없습니다.

이렇게 나누면 TLS 인증서와 외부 요청 처리는 Nginx에 모으고, PHP 작업 프로세스 수와 메모리는 애플리케이션 컨테이너에서 따로 관리할 수 있습니다.

## 3. Nginx 설정의 기본 단위

Nginx 설정은 여러 문맥으로 나뉩니다.

```nginx
http {
    server {
        listen 443 ssl;

        location / {
            # 요청 처리
        }
    }
}
```

- `http`: HTTP 전반의 설정을 둡니다.
- `server`: 주소, 포트와 서버 이름을 정합니다.
- `location`: 요청 URI에 따라 처리 방법을 고릅니다.

공식 Nginx 이미지는 `/etc/nginx/conf.d/*.conf`를 `http` 문맥 안에서 읽습니다. 프로젝트에서는 `server` 블록이 들어 있는 설정 파일만 추가할 수 있습니다.

설정 적용 전에 문법을 검사합니다.

```sh
nginx -t
docker compose exec gateway nginx -t
```

## 4. `listen`, `server_name`과 HTTP/2

```nginx
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    http2 on;
    server_name _;
}
```

`listen`은 Nginx가 어느 주소와 포트에서 연결을 받을지 정합니다. 여러 `server` 블록이 같은 포트를 사용하면 `Host` 헤더와 `server_name`을 비교해 처리할 블록을 선택합니다.

HTTP/2 설정 문법은 Nginx 버전에 따라 다를 수 있습니다. 설정을 옮길 때는 해당 이미지의 Nginx 버전과 `nginx -t` 결과를 확인합니다.

## 5. 정적 파일과 동적 요청

정적 파일은 Nginx가 직접 반환할 수 있습니다.

```nginx
location = /static.txt {
    root /usr/share/nginx/html;
    default_type text/plain;
}
```

PHP 애플리케이션으로 보낼 요청은 FastCGI 파라미터를 만들고 PHP-FPM에 전달합니다.

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

### `fastcgi_pass`

`app:9000`은 Compose 서비스 이름과 PHP-FPM 포트입니다. Nginx 컨테이너와 `app` 컨테이너가 같은 네트워크에 있어야 합니다.

### `SCRIPT_FILENAME`

PHP-FPM 컨테이너 안에서 실행할 실제 파일 경로입니다. Nginx 컨테이너의 경로가 아니라 PHP-FPM이 보는 경로와 맞아야 합니다.

```text
Nginx가 전달: /var/www/html/index.php
app 컨테이너: /var/www/html/index.php가 실제로 존재
```

FastCGI 연결이 성공해도 이 경로가 틀리면 `Primary script unknown`이나 파일을 찾지 못했다는 오류가 발생할 수 있습니다.

### `HTTPS on`

Nginx에서 TLS를 종료한 뒤 PHP-FPM에는 FastCGI 요청을 보냅니다. 애플리케이션이 원래 요청이 HTTPS였다는 사실을 알아야 할 때 이 값을 전달합니다.

## 6. TLS 파일

Nginx는 인증서와 개인키를 읽습니다.

```nginx
ssl_certificate /etc/nginx/tls/development.crt;
ssl_certificate_key /etc/nginx/tls/development.key;
ssl_protocols TLSv1.2 TLSv1.3;
```

- 개인키는 외부에 공개하면 안 됩니다.
- 인증서에는 공개키, 도메인 이름, 유효기간과 발급자 정보가 들어갑니다.
- 인증서와 개인키가 서로 맞지 않으면 Nginx가 시작하지 못합니다.

로컬 개발에서는 파일이 없을 때 자체 서명 인증서를 만들 수 있습니다.

```sh
openssl req -x509 -newkey rsa:2048 -nodes \
  -days 30 \
  -subj '/CN=localhost' \
  -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' \
  -keyout development.key \
  -out development.crt
```

개인키는 읽을 수 있는 사용자를 제한합니다.

```sh
chmod 600 development.key
```

자체 서명 인증서는 로컬 요청 경로를 확인하기 위한 수단입니다. 공인 서비스에서는 신뢰 가능한 인증서 체인과 갱신 절차가 필요합니다.

## 7. PHP-FPM의 프로세스 구성

PHP-FPM은 마스터 프로세스와 작업 프로세스로 실행됩니다.

```text
php-fpm master (PID 1)
├─ worker
├─ worker
└─ worker
```

컨테이너에서는 마스터를 포그라운드로 실행합니다.

```dockerfile
CMD ["php-fpm", "-F"]
```

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

`pm.max_children`은 동시에 처리할 PHP 요청 수의 상한이자 작업 프로세스 메모리 총량에 영향을 주는 값입니다. 크게 잡는다고 처리량이 자동으로 늘지 않습니다. 실제 작업 프로세스의 메모리와 요청 시간을 측정해 조정합니다.

## 8. 상태 검사 범위를 나눕니다

### Nginx만 확인

```nginx
location = /healthz {
    access_log off;
    default_type text/plain;
    return 200 "ok\n";
}
```

```sh
curl -kfsS https://127.0.0.1:19443/healthz
```

TLS와 Nginx의 HTTP 응답을 확인하지만 PHP-FPM과 데이터베이스는 확인하지 않습니다.

### PHP-FPM 확인

```sh
REQUEST_METHOD=GET \
SCRIPT_NAME=/ping \
SCRIPT_FILENAME=/ping \
cgi-fcgi -bind -connect 127.0.0.1:9000 | grep -q pong
```

FPM은 HTTP 서버가 아니므로 `curl http://127.0.0.1:9000`으로 검사하지 않습니다.

### 전체 요청 경로 확인

```sh
curl -kfsS https://127.0.0.1:19443/health
```

`/health`가 PHP 코드와 데이터베이스 읽기까지 수행한다면 Nginx, FastCGI, PHP-FPM과 데이터베이스를 함께 확인합니다.

얕은 `/healthz`와 전체 `/health`는 목적이 다릅니다. 하나가 성공한다고 다른 하나까지 성공하는 것은 아닙니다.

## 9. 오류를 나누어 확인하기

### 연결 거부

호스트 포트 게시, Nginx 프로세스와 수신 포트를 확인합니다.

```sh
docker compose ps -a
docker compose logs gateway
```

### TLS 오류

인증서 체인, SAN, 유효기간과 개인키 일치를 확인합니다.

```sh
openssl s_client -connect 127.0.0.1:19443 -servername localhost </dev/null
```

### 404

Nginx가 요청을 받았습니다. `location`, 경로와 정적 파일 위치를 확인합니다.

### 403

Nginx 작업 프로세스가 파일이나 상위 디렉터리를 읽지 못할 수 있습니다. 실행 사용자와 권한을 확인합니다.

### 502

Nginx가 PHP-FPM에 연결하지 못했거나 유효한 FastCGI 응답을 받지 못했습니다.

```text
app 컨테이너 상태
→ php-fpm 프로세스
→ 9000번 수신
→ gateway에서 app 이름 해석
→ app:9000 연결
→ FastCGI 설정
→ PHP 파일 경로
```

### 500

PHP 코드가 실행됐지만 처리 중 오류가 발생했을 가능성이 큽니다. PHP-FPM stderr와 애플리케이션 로그를 확인합니다.

## 10. 자주 생기는 오해

### PHP-FPM 포트에 `curl`을 보내면 됩니다

PHP-FPM은 FastCGI를 사용합니다. HTTP 클라이언트인 `curl`은 적절한 검사 도구가 아닙니다.

### 자체 서명 인증서도 암호화되므로 운영에서 안전합니다

암호화 연결은 만들 수 있지만 클라이언트가 서버 신원을 신뢰하게 만들지는 않습니다.

### 502는 PHP 코드 오류입니다

먼저 Nginx와 PHP-FPM 사이의 이름, 포트, 프로토콜과 파일 경로를 확인합니다. PHP 코드가 정상적으로 실행되어 500을 반환했다면 클라이언트는 보통 500을 받습니다.

## 확인 문제

1. Nginx와 PHP-FPM은 각각 어떤 프로토콜을 받습니까?
2. PHP-FPM의 9000번 포트를 호스트에 공개할 필요가 없는 이유는 무엇입니까?
3. `fastcgi_pass`와 `SCRIPT_FILENAME`은 각각 무엇을 지정합니까?
4. `/healthz`가 성공해도 `/health`가 502가 될 수 있는 이유는 무엇입니까?
5. `pm.max_children`을 지나치게 크게 설정하면 어떤 문제가 생길 수 있습니까?
6. `curl -k`가 운영 TLS 검증의 증거가 될 수 없는 이유는 무엇입니까?

## 참고 문서

- Nginx 요청 처리: https://nginx.org/en/docs/http/request_processing.html
- Nginx FastCGI: https://nginx.org/en/docs/http/ngx_http_fastcgi_module.html
- Nginx TLS: https://nginx.org/en/docs/http/ngx_http_ssl_module.html
- PHP-FPM 설정: https://www.php.net/manual/en/install.fpm.configuration.php
- OpenSSL `req`: https://docs.openssl.org/master/man1/openssl-req/
