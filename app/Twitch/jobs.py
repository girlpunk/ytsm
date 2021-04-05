import logging
import mimetypes

from YtManagerApp.IProvider import IProvider
from YtManagerApp.models import Video, Subscription
from Twitch import tasks
import requests
import twitch
from django.conf import settings


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
        return url.startswith("https://www.twitch.tv/")

    @staticmethod
    def process_url(url: str, subscription: Subscription):
        channel_name = url.split("/")[3]

        helix = twitch.Helix(settings.TWITCH_CLIENT_ID, settings.TWITCH_CLIENT_SECRET)

        channel_info = helix.user(channel_name)

        # No point in storing info about the 'uploads from X' playlist
        subscription.name = channel_info.display_name
        subscription.playlist_id = channel_info.id
        subscription.description = channel_info.description
        subscription.channel_id = channel_info.id
        subscription.channel_name = channel_info.login

        response = requests.get(channel_info.profile_image_url, stream=True)
        ext = mimetypes.guess_extension(response.headers['Content-Type'])
        file_name = f"{channel_info.id}{ext}"
        subscription.thumb.save(file_name, response.raw)

        subscription.save()
