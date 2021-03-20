# mysite/routing.py
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path


from YtManagerApp import consumers

application = ProtocolTypeRouter({
    'websocket': URLRouter([
        path('ytsm/ws/events/', consumers.EventConsumer.as_asgi()),
    ])
})
