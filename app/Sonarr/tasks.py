from threading import Lock
import logging

import datetime
from celery import shared_task

from pycliarr.api import SonarrCli
from Sonarr import utils

from YtManagerApp.models import *
from YtManagerApp.models import Video, Subscription
from typing import List

__api: SonarrCli = utils.get_api()
__log = logging.getLogger(__name__)
_ENABLE_UPDATE_STATS = False
__lock = Lock()


@shared_task
def synchronize_channel(channel_id: int):
    channel: Subscription = Subscription.objects.get(id=channel_id, provider="Sonarr")
    __log.info("Starting synchronize " + channel.name)
    videos = Video.objects.filter(subscription=channel)

    # Remove the 'new' flag
    videos.update(new=False)

    episodes: List[dict] = __api.get_episode(channel.channel_id)

    for episode in filter(lambda episode: episode["hasFile"], episodes):
        __log.info("Starting synchronize series "+episode.seriesId+", episode " + episode.absoluteEpisodeNumber)
        video, isNew = videos.update_or_create(video_id=episode["id"],
                                        subscription__pk=channel_id,
                                        defaults={
                                            "files": list(episode["episodeFile"]["path"]),
                                            "downloaded_path": episode["episodeFile"]["path"],
                                            "description": episode["overview"],
                                            "name": episode["title"],
                                            "subscription": channel,
                                            "playlist_index": episode["absoluteEpisodeNumber"],
                                            "publish_date": episode["airDate"]
                                        })[0]

        if isNew:
            video.watched = False
            video.new = True

        video.save()

    channel.last_synchronised = datetime.datetime.now(datetime.timezone.utc)
    channel.save()
