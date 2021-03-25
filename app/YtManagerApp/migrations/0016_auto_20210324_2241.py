# Generated by Django 3.0.3 on 2021-03-24 22:41

from django.conf import settings
from django.core.files import File
from django.db import migrations, models
from typing import TYPE_CHECKING
import os

if TYPE_CHECKING:
    from YtManagerApp.models import Subscription
    from YtManagerApp.models import Video


def create_subscription_images(apps, schema_editor):
    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, 'thumbs/sub/')):
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'thumbs/sub/'))
    subscription_model: Subscription = apps.get_model('YtManagerApp', 'Subscription')
    for subscription in subscription_model.objects.all():
        try:
            f = open(os.path.join(settings.MEDIA_ROOT, subscription.thumbnail.replace(settings.MEDIA_URL, "")))
            myimage = File(f)
            subscription.thumb.save("", myimage)
            subscription.save()
            f.close()
            os.unlink(os.path.join(settings.MEDIA_ROOT, subscription.thumbnail.replace(settings.MEDIA_URL, "")))
        except FileNotFoundError:
            pass


def create_video_images(apps, schema_editor):
    if not os.path.exists(os.path.join(settings.MEDIA_ROOT, 'thumbs/video/')):
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'thumbs/video/'))
    video_model: Video = apps.get_model('YtManagerApp', 'Video')
    for video in video_model.objects.all():
        try:
            f = open(os.path.join(settings.MEDIA_ROOT, video.thumbnail.replace(settings.MEDIA_URL, "")))
            myimage = File(f)
            video.thumb.save("", myimage)
            video.save()
            f.close()
            os.unlink(os.path.join(settings.MEDIA_ROOT, subscription.thumbnail.replace(settings.MEDIA_URL, "")))
        except FileNotFoundError:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('YtManagerApp', '0015_subscription_provider'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='thumb',
            field=models.ImageField(null=True, upload_to='thumbnails/sub'),
        ),
        migrations.AddField(
            model_name='video',
            name='thumb',
            field=models.ImageField(null=True, upload_to='thumbnails/video'),
        ),
        migrations.RunPython(create_subscription_images),
        migrations.RunPython(create_video_images)
    ]
