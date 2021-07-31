from YtManagerApp.models import settings

from pycliarr.api import SonarrCli


def get_api() -> SonarrCli:
    return SonarrCli(settings.SONARR_URL, settings.SONARR_API_KEY)
