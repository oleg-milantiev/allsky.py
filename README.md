# allsky.py
Питон+PHP скрипты для AllSky камеры из Raspberry/Orange Pi + ZWO / QHY / Starlight / .... любой INDI
Проверено на железе:
* Raspberry Pi 3 + Datyson t7c
* Raspberry Pi 3 + ZWO ASI 178c
* Orange Pi PC + Starlight Oculus

# Возможности
## Сейчас
Пока что это самое начало проекта и сейчас он может:
* поддерживать разные INDI камеры, задаваемые в config.py;
* подбирать выдержку от минимальной до максимальной заданной, стараясь среднее по средней части кадра держать в вилке 55...150 ADU;
* раз в минуту записывать файлы в папку локального веб-сервера, именуя их по дате / времени. Поддерживать актуальным файл (симлинк) последнего отснятого кадра;
* веб может показывать последний отснятый кадр и отображать дату / время его актуальности.

## В ближайших планах
Сроки размазаны, но планы чёткие:
* дать подробное описание установки (при следующем развёртывании сделаю);
* научить подбирать не только выдержку, но и bin / gain;
* расширить функционал веб-страницы (архив, просмотр за дату, ...);
* генерить мультики за сутки (с полдня по полдень) и за последний час (по запросу пользователя).

# Установка

## Ось

### Raspberry Pi
На Raspberry ставим Raspbian отсюда: https://www.raspberrypi.org/downloads/raspbian/

### Orange Pi
На апельсина ставим Armbian отсюда: https://www.armbian.com/download/ (выбери свою плату)

## Софт

### INDI

Использую INDI, хоть не все его любят. Потому как это правильно - использовать абстракцию для общения с любой камерой

@todo подробно опишу при следующем развёртывании
1. armbian, ssh, passwd, ...

2. нужные для камеры INDI компоненты
тут скачать архив https://indilib.org/download/raspberry-pi/download/6-raspberry-pi/9-indi-library-for-raspberry-pi.html -.
установить нужные для камеры пакеты (dpkg -i *deb)

3. supervisord
apt-get install supervisor
systemctl enable supervisor
Скопировать supervisor.conf в /etc/supervisor/conf.d
systemctl start supervisor

Проверка:
. supervisorctl status
..

4. модули к питону 3
apt-get install python3-pip python3-dev swig libnova-dev libatlas-base-dev imagemagick dcraw libwebp6 libjasper1 python3-gst-1.0 libqtgui4 libqt4-test
python3 -m pip install setuptools numpy pyindi-client astropy opencv-python
