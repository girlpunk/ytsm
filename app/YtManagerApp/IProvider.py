from abc import ABC, abstractmethod
from YtManagerApp.models import Video, Subscription


class IProvider(ABC):
    @staticmethod
    @abstractmethod
    def download_video(video: Video):
        pass

    @staticmethod
    @abstractmethod
    def synchronise_channel(subscription: Subscription):
        pass

    @staticmethod
    @abstractmethod
    def process_url(url: str, subscription: Subscription) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def is_url_valid_for_module(url: str) -> bool:
        pass
