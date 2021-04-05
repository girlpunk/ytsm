from threading import Lock

import requests
import twitch
from celery import shared_task

from YtManagerApp.models import *
from YtManagerApp.models import Video, Subscription

__log = logging.getLogger(__name__)
_ENABLE_UPDATE_STATS = False
__lock = Lock()
__api = twitch.Helix(settings.TWITCH_CLIENT_ID, settings.TWITCH_CLIENT_SECRET)


@shared_task
def synchronize_channel(channel_id: int):
    channel: Subscription = Subscription.objects.get(id=channel_id, provider="Twitch")
    __log.info("Starting synchronize " + channel.name)
    videos = Video.objects.filter(subscription=channel)

    # Remove the 'new' flag
    videos.update(new=False)

    channel_info = __api.user(channel.channel_id)
    response = requests.get(channel_info.profile_image_url, stream=True)
    ext = mimetypes.guess_extension(response.headers['Content-Type'])
    file_name = f"{channel_info.id}{ext}"
    channel.thumb.save(file_name, response.raw)

    __log.info("Starting check new videos " + channel.name)

    for item in __api.videos(user_id=channel.channel_id):
        results = Video.objects.filter(video_id=item.id, subscription=channel)

        if not results.exists():
            video = Video()
            video.video_id = item.id
            video.name = item.title.encode("ascii", errors="ignore").decode()
            video.description = item.description.encode("ascii", errors="ignore").decode()
            video.watched = False
            video.new = True
            video.downloaded_path = None
            video.subscription = channel
            video.playlist_index = 0
            video.publish_date = item.published_at

            response = requests.get(item.thumbnail_url, stream=True)
            ext = mimetypes.guess_extension(response.headers['Content-Type'])
            file_name = f"{item.id}{ext}"
            video.thumb.save(file_name, response.raw)

            video.save()

            synchronize_video(video)
    channel.last_synchronised = datetime.datetime.now()
    channel.save()

#    for video in videos:
#        synchronize_video(video)

    # enabled = first_non_null(channel.auto_download, channel.user.preferences['auto_download'])
    #
    # if enabled:
    #     global_limit = channel.user.preferences['download_global_limit']
    #     limit = first_non_null(channel.download_limit, channel.user.preferences['download_subscription_limit'])
    #     order = first_non_null(channel.download_order, channel.user.preferences['download_order'])
    #     order = VIDEO_ORDER_MAPPING[order]
    #
    #     videos_to_download = Video.objects \
    #         .filter(subscription=channel, downloaded_path__isnull=True, watched=False, subscription__auto_download=True) \
    #         .order_by(order)
    #
    #     if global_limit > 0:
    #         global_downloaded = Video.objects.filter(subscription__user=channel.user, downloaded_path__isnull=False).count()
    #         allowed_count = max(global_limit - global_downloaded, 0)
    #         videos_to_download = videos_to_download[0:allowed_count]
    #
    #     if limit > 0:
    #         sub_downloaded = Video.objects.filter(subscription=channel, downloaded_path__isnull=False).count()
    #         allowed_count = max(limit - sub_downloaded, 0)
    #         videos_to_download = videos_to_download[0:allowed_count]
    #
    #     # enqueue download
    #     for video in videos_to_download:
    #         download_video.delay(video.pk)


@shared_task
def actual_synchronize_video(video_id: int):
    video = Video.objects.get(id=video_id, subscription__provider="Twitch")
    __log.info("Starting synchronize video " + video.video_id)
    if video.downloaded_path is not None:
        try:
            files = list(video.get_files())
        except FileNotFoundError:
            files = []

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

    if _ENABLE_UPDATE_STATS or video.duration == 0:
        video_stats = __api.video(video.video_id)

        video.views = video_stats.view_count
        video.duration = video_stats.duration
        video.description = video_stats.description.encode("ascii", errors="ignore").decode()
        video.save()


@shared_task()
def download_video(video_pk: int, attempt: int = 1):
    raise NotImplemented
    # Issue: if multiple videos are downloaded at the same time, a race condition appears in the mkdirs() call that
    # youtube-dl makes, which causes it to fail with the error 'Cannot create folder - file already exists'.
    # For now, allow a single download instance.
    video = Video.objects.get(pk=video_pk, subscription__provider="Twitch")
    __lock.acquire()

    try:
        user = video.subscription.user
        max_attempts = user.preferences['max_download_attempts']

        youtube_dl_params, output_path = utils.build_youtube_dl_params(video)
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
    video = Video.objects.get(pk=video_pk, subscription__provider="Twitch")
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
