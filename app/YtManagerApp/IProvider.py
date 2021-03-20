from abc import ABC, abstractmethod
from YtManagerApp.models import Video, Subscription


class IProvider(ABC):
    @abstractmethod
    def download_video(self, video: Video):
        pass

    @abstractmethod
    def synchronise_channel(self, subscription: Subscription):
        pass

    @abstractmethod
    def process_url(self, url: str, subscription: Subscription) -> bool:
        pass

    @abstractmethod
    def is_url_valid_for_module(self, url: str) -> bool:
        pass
