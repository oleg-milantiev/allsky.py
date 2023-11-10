#docker build --squash -t olegmilantiev/allsky-indi-arm64 .
docker buildx build --push --platform linux/arm/v7,linux/arm64,linux/amd64 --squash -t olegmilantiev/allsky-ffmpeg .
