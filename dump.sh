#!/bin/sh

docker compose exec db mysqldump -pmaster allsky > db.sql
