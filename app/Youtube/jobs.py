from YtManagerApp.IProvider import IProvider
from YtManagerApp.models import Video, Subscription
from Youtube import tasks, youtube, utils
from external.pytaw.pytaw.youtube import Channel, Playlist, InvalidURL


class Jobs(IProvider):
    def synchronise_channel(self, subscription: Subscription):
        tasks.synchronize_channel.delay(subscription)

    def download_video(self, video: Video):
        tasks.download_video.delay(video)

    def delete_video(self, video: Video):
        tasks.delete_video.delay(video)

    def is_url_valid_for_module(self, url: str) -> bool:
        yt_api: youtube.YoutubeAPI = youtube.YoutubeAPI.build_public()

        try:
            yt_api.parse_url(url)
        except InvalidURL:
            return False
        return True

    def process_url(self, url: str, subscription: Subscription):
        yt_api: youtube.YoutubeAPI = youtube.YoutubeAPI.build_public()

        url_parsed = yt_api.parse_url(url)

        if 'playlist' in url_parsed:
            info_playlist = yt_api.playlist(url=url)
            if info_playlist is None:
                raise ValueError('Invalid playlist ID!')

            self._fill_from_playlist(subscription, info_playlist)
        else:
            info_channel = yt_api.channel(url=url)
            if info_channel is None:
                raise ValueError('Cannot find channel!')

            self._copy_from_channel(subscription, info_channel)

    @staticmethod
    def _fill_from_playlist(subscription: Subscription, info_playlist: Playlist):
        subscription.name = info_playlist.title
        subscription.playlist_id = info_playlist.id
        subscription.description = info_playlist.description
        subscription.channel_id = info_playlist.channel_id
        subscription.channel_name = info_playlist.channel_title
        subscription.thumbnail = utils.best_thumbnail(info_playlist).url
        subscription.save()

    @staticmethod
    def _copy_from_channel(subscription: Subscription, info_channel: Channel):
        # No point in storing info about the 'uploads from X' playlist
        subscription.name = info_channel.title
        subscription.playlist_id = info_channel.uploads_playlist.id
        subscription.description = info_channel.description
        subscription.channel_id = info_channel.id
        subscription.channel_name = info_channel.title
        subscription.thumbnail = utils.best_thumbnail(info_channel).url
        subscription.rewrite_playlist_indices = True
        subscription.save()
