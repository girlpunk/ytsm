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
        log.info("Trying to sync channel "+repr(channel))
        provider = channel.get_provider()
        log.info("Got provider "+repr(provider))
        provider.synchronise_channel(channel)
