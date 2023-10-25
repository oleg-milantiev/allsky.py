#!/bin/sh

# n - network size [n, s, m, l, x]
# 100 - epochs count
# 1 - version number

docker exec -it allsky-yolo /yolo/train.py n 20 1
