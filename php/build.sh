#docker build --squash -t olegmilantiev/allsky-php .
#docker buildx build --platform linux/amd64 --squash -t olegmilantiev/allsky-php .
docker buildx build --push --platform linux/arm64 --squash -t olegmilantiev/allsky-php-arm64 .
