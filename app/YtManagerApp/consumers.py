from django.db.models import Q

from YtManagerApp.models import JobExecution, JobMessage, JOB_STATES_MAP

from channels.generic.websocket import WebsocketConsumer
import json

class EventConsumer(WebsocketConsumer):
    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        request = text_data_json['request']

        if request == "jobs":
            self.jobs()

    def jobs(self):
        #TODO: User filtering
#| Q(user=request.user))\
        jobs = JobExecution.objects\
            .filter(status=JOB_STATES_MAP['running'])\
            .filter(Q(user__isnull=True))\
            .order_by('start_date')

        response = []

        for job in jobs:
            last_progress_message = JobMessage.objects\
                .filter(job=job, progress__isnull=False, suppress_notification=False)\
                .order_by('-timestamp').first()

            last_message = JobMessage.objects\
                .filter(job=job, suppress_notification=False)\
                .order_by('-timestamp').first()

            message = ''
            progress = 0

            if last_message is not None:
                message = last_message.message
            if last_progress_message is not None:
                progress = last_progress_message.progress

            response.append({
                'id': job.id,
                'description': job.description,
                'progress': progress,
                'message': message
            })

        self.send(text_data=json.dumps({
            'request': 'jobs',
            'data': response
        }))

    def connect(self):
        self.accept()
        self.jobs()

