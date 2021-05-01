# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.db.models import F

from YtManagerApp.models import *

log = logging.getLogger(__name__)

providers = {}


@shared_task
def synchronize_all():
    log.info("Starting synchronize all")
    channels = Subscription.objects.all().order_by(F('last_synchronised').desc(nulls_first=True))
    for channel in channels:
        channel.get_provider().synchronise_channel(channel)


@shared_task()
def synchronize_folder(folder_id: int):
    log.info("Starting sync folder")
    subscriptions = Subscription.objects.filter(parent_folder_id=folder_id)
    for subscription in subscriptions:
        subscription.get_provider().synchronise_channel(subscription)
