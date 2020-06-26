FROM python:3.6-alpine
COPY . /app
WORKDIR /app
RUN apk update && apk upgrade \
 && apk add --no-cache ca-certificates git openssl \
 && apk add --no-cache --virtual .build-dependencies libffi-dev openssl-dev build-base py3-pip python3-dev python2 make g++ \
 jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev harfbuzz-dev fribidi-dev \
 && pip install -r requirements.txt \
 && apk del .build-dependencies \
 && rm -rf /var/cache/*
CMD ["python3", "main.py"]
