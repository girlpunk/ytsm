FROM python:3

WORKDIR /opt/ytsm

# ffmpeg is needed for youtube-dl
RUN apt-get update
RUN apt-get install ffmpeg -y

COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ENV YTSM_DEBUG='False'
ENV YTSM_DATA_DIR='/data'
#ENV YTSM_CONFIG_DIR='/config'

VOLUME /data
VOLUME /download
#VOLUME /config

COPY ./app/ ./
#COPY ./config/ /config/ 
COPY ./docker/init.sh ./

EXPOSE 8000

CMD ["/bin/bash", "init.sh"]
