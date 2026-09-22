#docker build --squash -t olegmilantiev/allsky-indi-arm64 .

docker buildx build --push --platform linux/arm64,linux/amd64 -t olegmilantiev/allsky-indi .
#docker buildx build --platform linux/amd64 -t olegmilantiev/allsky-indi .
