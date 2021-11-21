import datetime
from django.http import HttpRequest
from xml.etree import ElementTree

from YtManagerApp.models import Video, Subscription
import tasks


def webhook(request: HttpRequest):
    rss = ElementTree.fromstring(request.body)
    for entry in rss.findall("{http://www.w3.org/2005/Atom}entry"):
        video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
        subscription_id = entry.find("{http://www.youtube.com/xml/schemas/2015}channelId").text

        results = Video.objects.get(video_id=video_id, subscription__channel_id=subscription_id, subscription__provider="Youtube")

        if results:
            tasks.synchronize_video(results)
        else:
            video_title = entry.find("{http://www.w3.org/2005/Atom}title").text

            video = Video()
            video.video_id = video_id
            video.name = video_title
            video.description = None
            video.watched = False
            video.new = True
            video.downloaded_path = None
            video.subscription = Subscription.objects.get(channel_id=subscription_id, provider="Youtube")
            video.playlist_index = 0
            video.publish_date = datetime.datetime.fromisoformat(entry.find("{http://www.w3.org/2005/Atom}published").text)
            video.save()

            tasks.synchronize_video(video)
