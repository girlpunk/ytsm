from channels.generic.websocket import WebsocketConsumer
import json

import datetime
import collections
import django_celery_results.models
from celery.result import AsyncResult
from typing import List, Optional


def flatten(item_list):
    for el in item_list:
        if isinstance(el, collections.Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten(el)
        else:
            yield el


class EventConsumer(WebsocketConsumer):
    http_user = True

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data:
            text_data_json = json.loads(text_data)
        elif bytes_data:
            text_data_json = json.loads(bytes_data)
        else:
            self.send(text_data=json.dumps({
                'request': 'error',
                'data': "Unable to find request body"
            }))
            return
        request = text_data_json['request']

        if request == "jobs":
            self.jobs()

    def jobs(self):
        all_children = []

        response = EventConsumer.search_recent_tasks("Synchronize All", all_children, "YtManagerApp.tasks.synchronize_all")
        response += EventConsumer.search_recent_tasks("Synchronize Folder", all_children, "YtManagerApp.tasks.synchronize_folder")
        response += EventConsumer.search_recent_tasks("Synchronize YouTube Channel", all_children, 'Youtube.tasks.synchronize_channel')
        response += EventConsumer.search_recent_tasks("Synchronize Twitch Channel", all_children, 'Twitch.tasks.synchronize_channel')

        self.send(text_data=json.dumps({
            'request': 'jobs',
            'data': response
        }))

    def connect(self):
        self.accept()
        self.jobs()

    @staticmethod
    def search_recent_tasks(description: str, all_children: List[str], task_name: Optional[str] = None):
        response = []

        tasks = django_celery_results.models.TaskResult.objects\
            .filter(
                task_name=task_name,
                date_created__gte=datetime.datetime.now()-datetime.timedelta(days=1))\
            .exclude(task_id__in=all_children)

        for task in tasks:
            all_children += [task.task_id]
            task = AsyncResult(task.task_id)

            complete_tasks = 0
            all_tasks = 0

            for child in flatten(task.graph.items()):
                if child.task_id not in all_children:
                    all_children.append(child.task_id)

                if child.successful():
                    complete_tasks += 1
                all_tasks += 1

            if all_tasks - complete_tasks == 0:
                continue

            progress = float(complete_tasks) / all_tasks

            response += [{
                'id': task.task_id,
                'description': description,
                'progress': progress,
                'message': str(complete_tasks) + " / " + str(all_tasks)
            }]

        return response
