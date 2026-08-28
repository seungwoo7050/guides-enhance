# syntax=docker/dockerfile:1
FROM nginx:stable-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        openssl \
    && rm -rf /var/lib/apt/lists/*

# [Implementation 8-2] Assemble the Nginx gateway image
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.sh /usr/local/bin/notes-gateway-entrypoint.sh
COPY static.txt /usr/share/nginx/html/static.txt
RUN chmod 0755 /usr/local/bin/notes-gateway-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/notes-gateway-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
