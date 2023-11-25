FROM php:8.2-fpm-alpine

RUN apk update && apk add --no-cache linux-headers oniguruma-dev libpng-dev libjpeg-turbo-dev
RUN docker-php-ext-install pdo_mysql mbstring sockets

RUN docker-php-ext-configure gd --with-jpeg --enable-gd 
RUN docker-php-ext-install gd

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer
COPY composer.json /var/www/composer.json

WORKDIR /var/www

RUN composer update

WORKDIR /var/www/html
