from threading import Lock
from xml.etree import ElementTree

import requests
import youtube_dl
from celery import shared_task
from django.db.models import Max

from Youtube import youtube
from Youtube.utils import build_youtube_dl_params, best_thumbnail
from YtManagerApp.management.downloader import fetch_thumbnail
from YtManagerApp.models import *
from YtManagerApp.models import Video, Subscription
from YtManagerApp.utils import first_non_null

__log = logging.getLogger(__name__)
_ENABLE_UPDATE_STATS = False
__api: youtube.YoutubeAPI = youtube.YoutubeAPI.build_public()
__lock = Lock()


@shared_task
def synchronize_channel(channel_id: int):
    channel = Subscription.objects.get(id=channel_id)
    __log.info("Starting synchronize "+channel.name)
    videos = Video.objects.filter(subscription=channel)

    # Remove the 'new' flag
    videos.update(new=False)

    __log.info("Starting check new videos " + channel.name)
    if channel.last_synchronised is None:
        check_all_videos(channel)
    else:
        check_rss_videos(channel)
    channel.last_synchronised = datetime.datetime.now()
    channel.save()

    fetch_missing_thumbnails_subscription.delay(channel.id)

    for video in videos:
        synchronize_video(video)

    enabled = first_non_null(channel.auto_download, channel.user.preferences['auto_download'])

    if enabled:
        global_limit = channel.user.preferences['download_global_limit']
        limit = first_non_null(channel.download_limit, channel.user.preferences['download_subscription_limit'])
        order = first_non_null(channel.download_order, channel.user.preferences['download_order'])
        order = VIDEO_ORDER_MAPPING[order]

        videos_to_download = Video.objects \
            .filter(subscription=channel, downloaded_path__isnull=True, watched=False) \
            .order_by(order)

        if global_limit > 0:
            global_downloaded = Video.objects.filter(subscription__user=channel.user, downloaded_path__isnull=False).count()
            allowed_count = max(global_limit - global_downloaded, 0)
            videos_to_download = videos_to_download[0:allowed_count]

        if limit > 0:
            sub_downloaded = Video.objects.filter(subscription=channel, downloaded_path__isnull=False).count()
            allowed_count = max(limit - sub_downloaded, 0)
            videos_to_download = videos_to_download[0:allowed_count]

        # enqueue download
        for video in videos_to_download:
            download_video.delay(video.pk)


@shared_task
def actual_synchronize_video(video_id: int):
    video = Video.objects.get(id=video_id)
    __log.info("Starting synchronize video "+video.video_id)
    if video.downloaded_path is not None:
        files = list(video.get_files())

        # Try to find a valid video file
        found_video = False
        for file in files:
            mime, _ = mimetypes.guess_type(file)
            if mime is not None and mime.startswith("video"):
                found_video = True

        # Video not found, we can safely assume that the video was deleted.
        if not found_video:
            # Clean up
            for file in files:
                os.unlink(file)
            video.downloaded_path = None

            # Mark watched?
            user = video.subscription.user
            if user.preferences['mark_deleted_as_watched']:
                video.watched = True

            video.save()

    fetch_missing_thumbnails_video.delay(video.id)

    if _ENABLE_UPDATE_STATS or video.duration == 0:
        video_stats = __api.video(video.video_id, part='id,statistics,contentDetails')

        if video_stats is None:
            return

        if video_stats.n_likes + video_stats.n_dislikes > 0:
            video.rating = video_stats.n_likes / (video_stats.n_likes + video_stats.n_dislikes)

        video.views = video_stats.n_views
        video.duration = video_stats.duration.total_seconds()
        video.save()


@shared_task
def fetch_missing_thumbnails_subscription(obj_id: int):
    obj = Subscription.objects.get(id=obj_id)
    if obj.thumbnail.startswith("http"):
        obj.thumbnail = fetch_thumbnail(obj.thumbnail, 'sub', obj.playlist_id, settings.THUMBNAIL_SIZE_SUBSCRIPTION)
        obj.save()


@shared_task
def fetch_missing_thumbnails_video(obj_id: int):
    obj = Video.objects.get(id=obj_id)
    if obj.thumbnail.startswith("http"):
        obj.thumbnail = fetch_thumbnail(obj.thumbnail, 'video', obj.video_id, settings.THUMBNAIL_SIZE_VIDEO)
        obj.save()


@shared_task()
def download_video(video_pk: int, attempt: int = 1):
    # Issue: if multiple videos are downloaded at the same time, a race condition appears in the mkdirs() call that
    # youtube-dl makes, which causes it to fail with the error 'Cannot create folder - file already exists'.
    # For now, allow a single download instance.
    video = Video.objects.get(pk=video_pk)
    __lock.acquire()

    try:
        user = video.subscription.user
        max_attempts = user.preferences['max_download_attempts']

        youtube_dl_params, output_path = build_youtube_dl_params(video)
        with youtube_dl.YoutubeDL(youtube_dl_params) as yt:
            ret = yt.download(["https://www.youtube.com/watch?v=" + video.video_id])

        __log.info('Download finished with code %d', ret)

        if ret == 0:
            video.downloaded_path = output_path
            video.save()
            __log.info('Video %d [%s %s] downloaded successfully!', video.id, video.video_id, video.name)

        elif attempt <= max_attempts:
            __log.warning('Re-enqueueing video (attempt %d/%d)', attempt, max_attempts)
            download_video.delay(video, attempt + 1)

        else:
            __log.error('Multiple attempts to download video %d [%s %s] failed!', video.id, video.video_id, video.name)
            video.downloaded_path = ''
            video.save()

    finally:
        __lock.release()


@shared_task()
def delete_video(video_pk: int):
    video = Video.objects.get(pk=video_pk)
    count = 0

    try:
        for file in video.get_files():
            __log.info("Deleting file %s", file)
            count += 1
            try:
                os.unlink(file)
            except OSError as e:
                __log.error("Failed to delete file %s: Error: %s", file, e)

    except OSError as e:
        __log.error("Failed to delete video %d [%s %s]. Error: %s",
                    video.id,
                    video.video_id,
                    video.name,
                    e)

    video.downloaded_path = None
    video.save()

    __log.info('Deleted video %d successfully! (%d files) [%s %s]',
               video.id,
               count,
               video.video_id,
               video.name)


def synchronize_video(video: Video):
    if video.downloaded_path is not None or _ENABLE_UPDATE_STATS or video.duration == 0:
        actual_synchronize_video.delay(video.id)

    if video.thumbnail.startswith("http"):
        fetch_missing_thumbnails_video.delay(video.id)


def check_rss_videos(sub: Subscription):
    found_existing_video = False

    rss_request = requests.get("https://www.youtube.com/feeds/videos.xml?channel_id="+sub.channel_id)
    rss_request.raise_for_status()

    rss = ElementTree.fromstring(rss_request.content)
    for entry in rss.findall("{http://www.w3.org/2005/Atom}entry"):
        video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
        results = Video.objects.filter(video_id=video_id, subscription=sub)
        if results.exists():
            found_existing_video = True
        else:
            video_title = entry.find("{http://www.w3.org/2005/Atom}title").text

            video = Video()
            video.video_id = video_id
            video.name = video_title
            video.description = entry.find("{http://search.yahoo.com/mrss/}group").find("{http://search.yahoo.com/mrss/}description").text or ""
            video.watched = False
            video.new = True
            video.downloaded_path = None
            video.subscription = sub
            video.playlist_index = 0
            video.publish_date = datetime.datetime.fromisoformat(entry.find("{http://www.w3.org/2005/Atom}published").text)
            video.thumbnail = entry\
                .find("{http://search.yahoo.com/mrss/}group")\
                .find("{http://search.yahoo.com/mrss/}thumbnail")\
                .get("url")
            video.rating = entry\
                .find("{http://search.yahoo.com/mrss/}group")\
                .find("{http://search.yahoo.com/mrss/}community")\
                .find("{http://search.yahoo.com/mrss/}starRating")\
                .get("average")
            video.views = entry\
                .find("{http://search.yahoo.com/mrss/}group")\
                .find("{http://search.yahoo.com/mrss/}community")\
                .find("{http://search.yahoo.com/mrss/}statistics")\
                .get("views")
            video.save()

            synchronize_video(video)

    if not found_existing_video:
        check_all_videos(sub)


def check_all_videos(sub: Subscription):
    playlist_items = __api.playlist_items(sub.playlist_id)
    if sub.rewrite_playlist_indices:
        playlist_items = sorted(playlist_items, key=lambda x: x.published_at)
    else:
        playlist_items = sorted(playlist_items, key=lambda x: x.position)

    for item in playlist_items:
        results = Video.objects.filter(video_id=item.resource_video_id, subscription=sub)

        if not results.exists():
            # fix playlist index if necessary
            if sub.rewrite_playlist_indices or Video.objects.filter(subscription=sub, playlist_index=item.position).exists():
                highest = Video.objects.filter(subscription=sub).aggregate(Max('playlist_index'))['playlist_index__max']
                item.position = 1 + (highest or -1)

            video = Video()
            video.video_id = item.resource_video_id
            video.name = item.title
            video.description = item.description
            video.watched = False
            video.new = True
            video.downloaded_path = None
            video.subscription = sub
            video.playlist_index = item.position
            video.publish_date = item.published_at
            video.thumbnail = best_thumbnail(item).url
            video.save()

            synchronize_video(video)
