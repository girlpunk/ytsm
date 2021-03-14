# mysite/routing.py
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path
from django.urls import path
import YtManagerApp.routing

#application = ProtocolTypeRouter({
#    'websocket': AuthMiddlewareStack(
#        URLRouter(
#            YtManagerApp.routing.websocket_urlpatterns
#        )
#    ),
#})

from YtManagerApp import consumers

application = ProtocolTypeRouter({
    'websocket': URLRouter([
        path('ytsm/ws/events/', consumers.EventConsumer.as_asgi()),
    ])
})


