FROM python:3

WORKDIR /opt/ytsm

# ffmpeg is needed for youtube-dl
RUN apt-get update && apt-get install -y \
    ffmpeg \
    mysql-client\
  && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

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

CMD ["/bin/bash", "init.sh"]
