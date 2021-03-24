import logging

import os
from django.contrib.auth.models import User

from YtManagerApp.models import Video, Subscription, VIDEO_ORDER_MAPPING
from YtManagerApp.utils import first_non_null

log = logging.getLogger('downloader')
log.setLevel(os.environ.get('LOGLEVEL', 'INFO').upper())


def __get_subscription_config(sub: Subscription):
    user: User = sub.user

    enabled = first_non_null(sub.auto_download, user.preferences['auto_download'])
    global_limit = user.preferences['download_global_limit']
    limit = first_non_null(sub.download_limit, user.preferences['download_subscription_limit'])
    order = first_non_null(sub.download_order, user.preferences['download_order'])
    order = VIDEO_ORDER_MAPPING[order]

    return enabled, global_limit, limit, order


def downloader_process_subscription(sub: Subscription):
    log.info('Processing subscription %d [%s %s]', sub.id, sub.playlist_id, sub.id)

    enabled, global_limit, limit, order = __get_subscription_config(sub)
    log.info('Determined settings enabled=%s global_limit=%d limit=%d order="%s"', enabled, global_limit, limit, order)

    if enabled:
        videos_to_download = Video.objects\
            .filter(subscription=sub, downloaded_path__isnull=True, watched=False)\
            .order_by(order)

        log.info('%d download candidates.', len(videos_to_download))

        if global_limit > 0:
            global_downloaded = Video.objects.filter(subscription__user=sub.user, downloaded_path__isnull=False).count()
            allowed_count = max(global_limit - global_downloaded, 0)
            videos_to_download = videos_to_download[0:allowed_count]
            log.info('Global limit is set, can only download up to %d videos.', allowed_count)

        if limit > 0:
            sub_downloaded = Video.objects.filter(subscription=sub, downloaded_path__isnull=False).count()
            allowed_count = max(limit - sub_downloaded, 0)
            videos_to_download = videos_to_download[0:allowed_count]
            log.info('Limit is set, can only download up to %d videos.', allowed_count)

        # enqueue download
        for video in videos_to_download:
            log.info('Enqueuing video %d [%s %s] index=%d', video.id, video.video_id, video.name, video.playlist_index)
            video.subscription.get_provider().download_video(video)

    log.info('Finished processing subscription %d [%s %s]', sub.id, sub.playlist_id, sub.id)


def downloader_process_all():
    for subscription in Subscription.objects.all():
        downloader_process_subscription(subscription)
