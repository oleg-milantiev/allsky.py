#FROM php:8.1-fpm
#RUN docker-php-ext-install pdo_mysql mbstring

FROM php:8.1-fpm-alpine

RUN apk update && apk add oniguruma-dev
RUN docker-php-ext-install pdo_mysql mbstring sockets

WORKDIR /var/www/html
