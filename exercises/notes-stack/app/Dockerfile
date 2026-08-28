# syntax=docker/dockerfile:1
FROM php:8.3-fpm-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libfcgi-bin \
    && docker-php-ext-install pdo_mysql \
    && rm -rf /var/lib/apt/lists/*

# [Implementation 7] Assemble the PHP-FPM application image
COPY www.conf /usr/local/etc/php-fpm.d/www.conf
COPY docker-entrypoint.sh /usr/local/bin/app-entrypoint.sh
COPY bin/bootstrap.php /opt/app/bootstrap.php
COPY public/ /var/www/html/
RUN chmod 0755 /usr/local/bin/app-entrypoint.sh \
    && chown -R www-data:www-data /var/www/html

WORKDIR /var/www/html
ENTRYPOINT ["/usr/local/bin/app-entrypoint.sh"]
CMD ["php-fpm", "-F"]
