from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import View

from YtManagerApp import tasks
from YtManagerApp.management.jobs.synchronize import SynchronizeJob
from YtManagerApp.models import Video, Subscription


class SyncNowView(LoginRequiredMixin, View):
    def post(self, *args, **kwargs):
        if 'pk' in kwargs:
            tasks.synchronize_channel.delay(kwargs['pk'])
        else:
            tasks.synchronize_all.delay()
        return JsonResponse({
            'success': True
        })


class DeleteVideoFilesView(LoginRequiredMixin, View):
    def post(self, **kwargs):
        video = Video.objects.get(id=kwargs['pk'])
        video.delete_files()
        return JsonResponse({
            'success': True
        })


class DownloadVideoFilesView(LoginRequiredMixin, View):
    def post(self, **kwargs):
        video = Video.objects.get(id=kwargs['pk'])
        video.download()
        return JsonResponse({
            'success': True
        })


class MarkVideoWatchedView(LoginRequiredMixin, View):
    def post(self, *args, **kwargs):
        videos = Video.objects.filter(id__in=kwargs['pk'].split(","))
        videos.update(watched=True)

        for video in videos:
            video.mark_watched()
            video.save()

        return JsonResponse({
            'success': True
        })


class MarkVideoUnwatchedView(LoginRequiredMixin, View):
    def post(self, **kwargs):
        video = Video.objects.get(id=kwargs['pk'])
        video.mark_unwatched()
        video.save()
        return JsonResponse({
            'success': True
        })
