from external.pytaw.pytaw.youtube import InvalidURL

from Youtube import tasks, youtube, utils
from YtManagerApp.IProvider import IProvider
from YtManagerApp.models import Video, Subscription


class Jobs(IProvider):
    @staticmethod
    def synchronise_channel(subscription: Subscription):
        tasks.synchronize_channel.delay(subscription.pk)

    @staticmethod
    def download_video(video: Video):
        tasks.download_video.delay(video.pk)

    @staticmethod
    def delete_video(video: Video):
        tasks.delete_video.delay(video.pk)

    @staticmethod
    def is_url_valid_for_module(url: str) -> bool:
        yt_api: youtube.YoutubeAPI = youtube.YoutubeAPI.build_public()

        try:
            yt_api.parse_url(url)
        except InvalidURL:
            return False
        return True

    @staticmethod
    def process_url(url: str, subscription: Subscription):
        yt_api: youtube.YoutubeAPI = youtube.YoutubeAPI.build_public()

        url_parsed = yt_api.parse_url(url)

        if 'playlist' in url_parsed:
            info_playlist = yt_api.playlist(url=url)
            if info_playlist is None:
                raise ValueError('Invalid playlist ID!')

            utils.fill_from_playlist(subscription, info_playlist)
        else:
            info_channel = yt_api.channel(url=url)
            if info_channel is None:
                raise ValueError('Cannot find channel!')

            utils.copy_from_channel(subscription, info_channel)
