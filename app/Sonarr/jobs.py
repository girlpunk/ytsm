import logging
import urllib.parse
import requests
import mimetypes

from pycliarr.api import SonarrCli, SonarrSerieItem
from Sonarr import tasks, utils
from YtManagerApp.IProvider import IProvider
from django.conf import settings
from YtManagerApp.models import Video, Subscription
from typing import List, Callable


class Jobs(IProvider):
    @staticmethod
    def synchronise_channel(subscription: Subscription):
        tasks.synchronize_channel.delay(subscription.pk)

    @staticmethod
    def download_video(video: Video):
        logging.getLogger(__name__).warning("Downloading videos is not supported for Sonarr")

    @staticmethod
    def delete_video(video: Video):
        logging.getLogger(__name__).warning("Downloading videos is not supported for Sonarr")

    @staticmethod
    def is_url_valid_for_module(url: str) -> bool:

        return url.startswith(settings.SONARR_URL)

    @staticmethod
    def process_url(url: str, subscription: Subscription):
        sonarr_api: SonarrCli = utils.get_api()

        url_title = urllib.parse.urlparse(url).path.split("/")[2]

        all_series: List[SonarrSerieItem] = sonarr_api.get_serie()

        filter_func: Callable[[SonarrSerieItem], bool] = lambda item: item.titleSlug == url_title
        matching_series: SonarrSerieItem = list(filter(filter_func, all_series))

        if matching_series and (len(matching_series) == 1):
            series = matching_series[0]
        else:
            raise ValueError("Invalid URL - Unable to match show from Sonarr")

        subscription.name = series.title
        subscription.playlist_id = series.id
        subscription.description = series.overview
        subscription.channel_id = series.id
        subscription.channel_name = series.network

        response = requests.get(series.images[0].remoteUrl, stream=True)
        ext = mimetypes.guess_extension(response.headers['Content-Type'])
        file_name = f"{series.id}{ext}"

        subscription.thumb.save(file_name, response.raw)

        subscription.save()
0