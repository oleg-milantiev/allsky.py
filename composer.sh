docker run --env-file=.env --rm -it -v /opt/allsky.py:/opt/allsky.py \
  -w /opt/allsky.py allskypy_php ./composer.phar update
