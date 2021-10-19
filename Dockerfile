FROM python:3.10-alpine
ENV PYTHONUNBUFFERED 1
WORKDIR /opt/ytsm

# ffmpeg is needed for youtube-dl
#RUN apt-get update && apt-get install -y \
#    ffmpeg \
#    mariadb-client\
#  && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./

RUN apk add --no-cache --virtual .build-deps ffmpeg mariadb-client mariadb-dev build-base libffi-dev rust cargo jpeg-dev python3-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del build-base rust cargo python3-dev

ENV YTSM_DEBUG='False'
ENV YTSM_DATA_DIR='/data'
ENV PYTHONUNBUFFERED=TRUE
ENV YTSM_CONFIG_DIR='/config'

VOLUME /data
VOLUME /download
VOLUME /config

COPY ./app/ ./
COPY ./config/ /config/ 
COPY ./docker/init.sh ./

EXPOSE 8000

CMD ["/bin/sh", "init.sh"]
