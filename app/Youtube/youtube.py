from typing import Optional

from external.pytaw.pytaw.youtube import YouTube, Thumbnail, Resource


class YoutubeAPI(YouTube):

    @staticmethod
    def build_public() -> 'YoutubeAPI':
        from YtManagerApp.management.appconfig import appconfig
        return YoutubeAPI(key=appconfig.youtube_api_key)

    # @staticmethod
    # def build_oauth() -> 'YoutubeAPI':
    #     flow =
    #     credentials =
    #     service = build(API_SERVICE_NAME, API_VERSION, credentials)


def default_thumbnail(resource: Resource) -> Optional[Thumbnail]:
    """
    Gets the default thumbnail for a resource.
    Searches in the list of thumbnails for one with the label 'default', or takes the first one.
    :param resource:
    :return:
    """
    thumbs = getattr(resource, 'thumbnails', None)

    if thumbs is None or len(thumbs) <= 0:
        return None

    return next(
        (i for i in thumbs if i.id == 'default'),
        thumbs[0]
    )
