FROM python:3.6-alpine
COPY . /app
WORKDIR /app
RUN apk update && apk upgrade \
 && apk add --no-cache ca-certificates git \
 && apk add --no-cache --virtual .build-dependencies python2 make g++ \
 && pip install -r requirements.txt \
 && apk del .build-dependencies \
 && rm -rf /var/cache/*
CMD ["python3", "main.py"]

