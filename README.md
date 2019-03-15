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
* раз в минуту записывать файлы в папку локального веб-сервера, именуя их по дате / времени;
* поддерживать актуальным файл (симлинк) последнего отснятого кадра;
* удалять старые файлы (выходящие за кол-во дней, указанных в конфиге);
* веб может показывать последний отснятый кадр и отображать дату / время его актуальности.

## В ближайших планах
Сроки размазаны, но планы чёткие. Описаны на страницах планирования гитхаба https://github.com/oleg-milantiev/allsky.py/milestones 

# Установка

## Ось

### Raspberry Pi
На Raspberry ставим Raspbian отсюда: https://www.raspberrypi.org/downloads/raspbian/

### Orange Pi
На апельсина ставим Armbian отсюда: https://www.armbian.com/download/ (выбери свою плату)

### Tinkerboard / S
На этом мини-компе так же ставим Armbian отсюда: https://www.armbian.com/tinkerboard/

## Софт

### INDI

Использую INDI, хоть не все его любят. Потому как это правильно - использовать абстракцию для общения с любой камерой

*Черновик черновика*
1. armbian на Tinkerboard / S
Первый вход root / 1234
Предлагает создать пользователя. Лучше создать. Просто так не отстанет :)

2. Обновить и установить нужные пакеты из армианной кучи
apt update
apt upgrade

apt install mc supervisor
apt install fontconfig-config fonts-dejavu-core libcairo2 libcfitsio5 libfontconfig1 libfreetype6 libgsl2 libjpeg62-turbo libnova-0.16-0 libogg0 libpixman-1-0 libtheora0 libusb-1.0-0-dev libx11-6 libx11-data libxau6 libxcb-render0 libxcb-shm0 libxcb1 libxdmcp6 libxext6 libxrender1 python3-pip python3-dev python3-setuptools

3. Скачать и установить INDI сервер и драйвер камеры
cd /root
mkdrir install
cd install
wget https://indilib.org/download/raspberry-pi/send/6-raspberry-pi/9-indi-library-for-raspberry-pi.html
tar xzf 9-indi-library-for-raspberry-pi.html
rm -f 9-indi-library-for-raspberry-pi.html
cd libindi_1.7.4_rpi
dpkg -i indi-bin_1.7.4_armhf.deb libindi-data_1.7.4_all.deb libindi-dev_1.7.4_armhf.deb libindi1_1.7.4_armhf.deb 
(плюс ещё *deb для своей камеры)
QHY: dpkg -i indi-qhy_1.8_armhf.deb libqhy_2.0.10_armhf.deb fxload_1.0_armhf.deb

4. Установить нужные для python модули (библиотеки)
python3 -m pip install numpy pyindi-client astropy opencv-python

5. Скачать код проекта
cd /root
git clone https://github.com/oleg-milantiev/allsky.py.git
cd allsky.py

6. Запустить allsky.py демона под управлением супердемона! :)
cp /root/allsky.py/supervisor.conf/* /etc/supervisor/conf.d/
systemctl enable supervisor
systemctl start supervisor



----



4. модули к питону 3
apt-get install python3-pip python3-dev swig libnova-dev libatlas-base-dev imagemagick dcraw libwebp6 libjasper1 python3-gst-1.0 libqtgui4 libqt4-test
python3 -m pip install setuptools numpy pyindi-client astropy opencv-python

5. Скачать код проекта и скопировать конфиги из него
5. корректная timezone
apt install git dialog
git clone https://github.com/armbian/config.git
debian-config <--- timezone на МСК
systemctl restart apache2

cp -r /root/allsky/var-www-html/* /var/www/html
rm -f /var/www/html/index.html
