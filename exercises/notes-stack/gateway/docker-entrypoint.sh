#!/bin/sh
set -eu

# [Implementation 8] Create missing local TLS files
cert_dir=/etc/nginx/tls
cert_file="$cert_dir/development.crt"
key_file="$cert_dir/development.key"
cert_cn=${CERT_CN:-localhost}

install -d -m 0755 "$cert_dir"
if [ ! -s "$cert_file" ] || [ ! -s "$key_file" ]; then
    openssl req -x509 -newkey rsa:2048 -nodes \
        -days 30 \
        -subj "/CN=$cert_cn" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
        -keyout "$key_file" \
        -out "$cert_file" >/dev/null 2>&1
    chmod 0600 "$key_file"
    chmod 0644 "$cert_file"
fi

exec /docker-entrypoint.sh "$@"
