FROM php:8.1-fpm-alpine

RUN apk update && apk add oniguruma-dev
RUN docker-php-ext-install pdo_mysql mbstring sockets

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer
COPY composer.json /var/www/composer.json

WORKDIR /var/www

RUN composer update

WORKDIR /var/www/html
