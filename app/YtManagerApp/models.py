import logging
import mimetypes

import importlib
import os
import datetime
from typing import Callable, Union, Any, Optional, TYPE_CHECKING

from django.db import models
from django.db.models.functions import Lower
from django.contrib.auth.models import User
from django.conf import settings

# help_text = user shown text
# verbose_name = user shown name
# null = nullable, blank = user is allowed to set value to empty

if TYPE_CHECKING:
    from YtManagerApp.IProvider import IProvider

VIDEO_ORDER_CHOICES = [
    ('newest', 'Newest'),
    ('oldest', 'Oldest'),
    ('playlist', 'Playlist order'),
    ('playlist_reverse', 'Reverse playlist order'),
    ('popularity', 'Popularity'),
    ('rating', 'Top rated'),
]

VIDEO_ORDER_MAPPING = {
    'newest': '-publish_date',
    'oldest': 'publish_date',
    'playlist': 'playlist_index',
    'playlist_reverse': '-playlist_index',
    'popularity': '-views',
    'rating': '-rating'
}


class SubscriptionFolder(models.Model):
    name = models.CharField(null=False, max_length=250)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=False)

    class Meta:
        ordering = [Lower('parent__name'), Lower('name')]

    def __str__(self):
        s = ""
        current = self
        while current is not None:
            s = current.name + " > " + s
            current = current.parent
        return s[:-3]

    def __repr__(self):
        return f'folder {self.id}, name="{self.name}"'

    def get_unwatched_count(self):
        def count(node: Union["SubscriptionFolder", "Subscription"]):
            if node.pk != self.pk:
                return node.get_unwatched_count()

        return sum(SubscriptionFolder.traverse(self.id, self.user, count))

    def delete_folder(self, keep_subscriptions: bool):
        if keep_subscriptions:

            def visit(node: Union["SubscriptionFolder", "Subscription"]):
                if isinstance(node, Subscription):
                    node.parent_folder = None
                    node.save()

            SubscriptionFolder.traverse(self.id, self.user, visit)

        self.delete()

    @staticmethod
    def traverse(root_folder_id: Optional[int],
                 user: 'User',
                 visit_func: Callable[[Union["SubscriptionFolder", "Subscription"]], Any]):

        data_collected = []

        def collect(data):
            if data is not None:
                data_collected.append(data)

        # Visit root
        if root_folder_id is not None:
            root_folder = SubscriptionFolder.objects.get(id=root_folder_id)
            collect(visit_func(root_folder))

        queue = [root_folder_id]
        visited = []

        while len(queue) > 0:
            folder_id = queue.pop()

            if folder_id in visited:
                logging.error('Found folder tree cycle for folder id %d.', folder_id)
                continue
            visited.append(folder_id)

            for folder in SubscriptionFolder.objects.filter(parent_id=folder_id, user=user).order_by(Lower('name')):
                collect(visit_func(folder))
                queue.append(folder.id)

            for subscription in Subscription.objects.filter(parent_folder_id=folder_id, user=user).order_by(Lower('name')):
                collect(visit_func(subscription))

        return data_collected


class Subscription(models.Model):
    name = models.CharField(null=False, max_length=1024)
    parent_folder = models.ForeignKey(SubscriptionFolder, on_delete=models.CASCADE, null=True, blank=True)
    playlist_id = models.CharField(null=False, max_length=128)
    description = models.TextField()
    channel_id = models.CharField(max_length=128)
    channel_name = models.CharField(max_length=1024)
    thumbnail = models.CharField(max_length=1024)
    thumb = models.ImageField(upload_to="thumbnails/sub", null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # youtube adds videos to the 'Uploads' playlist at the top instead of the bottom
    rewrite_playlist_indices = models.BooleanField(default=False)
    last_synchronised = models.DateTimeField(null=True, blank=True)
    provider = models.CharField(null=False, blank=False, max_length=64)

    # overrides
    auto_download = models.BooleanField(null=True, blank=True)
    download_limit = models.IntegerField(null=True, blank=True)
    download_order = models.CharField(
        null=True, blank=True,
        max_length=128,
        choices=VIDEO_ORDER_CHOICES)
    automatically_delete_watched = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'subscription {self.id}, name="{self.name}", playlist_id="{self.playlist_id}"'

    def delete_subscription(self, keep_downloaded_videos: bool):
        self.delete()

    def synchronize_now(self):
        self.get_provider().synchronise_channel(self)

    def get_unwatched_count(self):
        return Video.objects.filter(subscription=self, watched=False).count()

    def get_provider(self) -> 'IProvider':
        if self.provider not in settings.INSTALLED_PROVIDERS:
            raise Exception("Provider "+self.provider+" not loaded for subscription "+self.name+" ("+str(self.id)+")")
        return importlib.import_module(self.provider+".jobs").Jobs


class Video(models.Model):
    video_id = models.CharField(null=False, max_length=12)
    name = models.TextField()
    description = models.TextField()
    watched = models.BooleanField(default=False)
    new = models.BooleanField(default=True)
    downloaded_path = models.TextField(null=True, blank=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    playlist_index = models.IntegerField()
    publish_date = models.DateTimeField(null=False)
    thumbnail = models.TextField()
    thumb = models.ImageField(upload_to="thumbnails/video", null=True)
    uploader_name = models.CharField(null=False, max_length=255)
    views = models.IntegerField(default=0)
    rating = models.FloatField(default=0.5)
    duration = models.IntegerField(default=0)

    def mark_watched(self):
        self.watched = True
        self.save()
        if self.downloaded_path is not None:
            from YtManagerApp.management.appconfig import appconfig
            if appconfig.for_sub(self.subscription, 'automatically_delete_watched'):
                # self.subscription.get_provider().download_video(self)
                self.subscription.get_provider().synchronise_channel(self.subscription)

    def mark_unwatched(self):
        self.watched = False
        self.save()
        self.subscription.get_provider().synchronise_channel(self.subscription)

    def get_files(self):
        if self.downloaded_path is not None:
            directory, file_pattern = os.path.split(self.downloaded_path)
            for file in os.listdir(directory):
                if file.startswith(file_pattern):
                    yield os.path.join(directory, file)

    def find_video(self):
        """
        Finds the video file from the downloaded files, and
        returns
        :return: Tuple containing file path and mime type
        """
        for file in self.get_files():
            mime, _ = mimetypes.guess_type(file)
            if mime is not None and mime.startswith('video/'):
                return file, mime

        return None, None

    def delete_files(self):
        for file in self.get_files():
            os.unlink(file)
        self.downloaded_path = None
        self.save()
        self.subscription.get_provider().synchronise_channel(self.subscription)

    def download(self):
        if not self.downloaded_path:
            self.subscription.get_provider().download_video(self)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'video {self.id}, video_id="{self.video_id}"'

    @property
    def duration_string(self):
        return str(datetime.timedelta(seconds=self.duration))


JOB_STATES = [
    ('running', 0),
    ('finished', 1),
    ('failed', 2),
    ('interrupted', 3),
]

JOB_STATES_MAP = {
    'running': 0,
    'finished': 1,
    'failed': 2,
    'interrupted': 3,
}

JOB_MESSAGE_LEVELS = [
    ('normal', 0),
    ('warning', 1),
    ('error', 2),
]
JOB_MESSAGE_LEVELS_MAP = {
    'normal': 0,
    'warning': 1,
    'error': 2,
}


class JobExecution(models.Model):
    start_date = models.DateTimeField(auto_now=True, null=False)
    end_date = models.DateTimeField(null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    description = models.CharField(max_length=250, null=False, default="")
    status = models.IntegerField(choices=JOB_STATES, default=0)


class JobMessage(models.Model):
    timestamp = models.DateTimeField(auto_now=True, null=False)
    job = models.ForeignKey(JobExecution, null=False, on_delete=models.CASCADE)
    progress = models.FloatField(null=True)
    message = models.CharField(max_length=1024, null=False, default="")
    level = models.IntegerField(choices=JOB_MESSAGE_LEVELS, default=0)
    suppress_notification = models.BooleanField(default=False)
