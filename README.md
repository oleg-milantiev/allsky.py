English version below.

# allsky.py

Питон+PHP скрипты для AllSky камеры из Raspberry/Orange Pi + ZWO / QHY / Starlight / .... любой INDI.

Проверено на железе:
* Raspberry Pi 3 + Datyson t7c / t7m (драйвер ZWO ASI 120)
* Raspberry Pi 3 + ZWO ASI 178c
* Orange Pi PC + Starlight Oculus / QHY5 старая шайба чб (через fxload и INDI qhy)
* Tinkerboard / S + QHY5-II
* i7 x64 + Starlight Oculus

# Возможности

## Сейчас

Сейчас проект может:
* поддерживать любые INDI камеры, найденные через list.py;
* подбирать выдержку от минимальной до максимальной заданной, стараясь среднее по средней части кадра держать в заданной вилке (например, 55...150 ADU);
* раз в минуту записывать файлы в папку локального веб-сервера, именуя их по дате / времени;
* публиковать картинку и / или данные сенсоров на публичный сайт проекта;
* снабжать кадр timestamp'ом, то есть указанием даты и времени (настраивается) и другими аннотациями;
* поддерживать актуальным файл (симлинк) последнего отснятого кадра;
* удалять старые файлы (выходящие за кол-во дней, указанных в конфиге);
* ежеминутно сохранять данные по выдержке / среднему, данные с датчиков (температура, влажность, давление, ...);
* собирать видеоролик и keogram ежесуточно (через час после рассвета за всю ночь);
* веб может показывать:
  * последний отснятый кадр и отображать дату / время его актуальности;
  * любой кадр из архива с возможностью листать кадры с клавиатуры или кликом в вебе;
  * собранные видеоролики и keogram;
  * графики с датчиков в разрезе за разное время (час, сутки, неделя, месяц).
* веб может управлять:
  * платой реле / мосфетов / ключей для управления нагрузками;
  * настраивать работу allsky.

Подробнее в вики проекта: https://github.com/oleg-milantiev/allsky.py/wiki

## В ближайших планах

Сроки размазаны, но планы чёткие. Описаны на страницах планирования гитхаба https://github.com/oleg-milantiev/allsky.py/milestones 
Участвуй в проекте! Роль найдётся каждому. Можно просто придумывать хотелки и писать их в Issues гитхаба: https://github.com/oleg-milantiev/allsky.py/issues . Но, возможно, твоя роль в чём-то большем?

# Установка

Подробно описана в вики проекта на соответствующей странице: https://github.com/oleg-milantiev/allsky.py/wiki/install

-------

English version.

# allsky.py

Python+PHP scripts for using Raspberry/Orange Pi + ZWO / QHY / Starlight / .... with any INDI as AllSky camera.

Successfully checked on:
* Raspberry Pi 3 + Datyson t7c / t7m (with ZWO ASI 120 driver)
* Raspberry Pi 3 + ZWO ASI 178c
* Orange Pi PC + Starlight Oculus / QHY5 old (via fxload and INDI qhy)
* Tinkerboard / S + QHY5-II
* i7 (x64) + Starlight Oculus

# Features

## Now

At moment project can:
* support any INDI cameras. You could find it via list.py;
* adjust exposure / binning and gain to keep center image average at needed range (for example, 55...150 ADU);
* every minute store fit and jpg files with camera snapshot;
* publish jpg and / or sensor data to public web;
* annotate snap with datetime, text, sensor data;
* actualize current.jpg symlink;
* remove (rotate) old fit, jpg and mp4 files (may be controlled in web);
* every minute store sensor data (temperature, humidity, presure, ADC values, CCD sensor data, star detect and AI cloud propability);
* create night video and keogram every morning (at sunrise plus hour);
* web could do:
  * show last (current) jpg;
  * show any old jpeg in archive;
  * show night video and keogram;
  * draw charts for different sensors for hour, day, week, months.
* web could control:
  * relay / mosfet board for control AC or DC loads;
  * configure allsky settings.

Please look at project wiki: https://github.com/oleg-milantiev/allsky.py/wiki

## To be done

We have plans, divided by milestones at github https://github.com/oleg-milantiev/allsky.py/milestones 
Join the project! You could create issues at: https://github.com/oleg-milantiev/allsky.py/issues . Maybe you could contribute?

# Install

Install manual is described at wiki: https://github.com/oleg-milantiev/allsky.py/wiki/install
