#!/bin/sh

docker exec -i allsky-db mysql -pmaster allsky < db.sql
