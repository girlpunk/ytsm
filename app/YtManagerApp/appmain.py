import logging
import logging.handlers
import sys

import os
from django.conf import settings as dj_settings


def __initialize_logger():
    log_dir = os.path.join(dj_settings.DATA_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    logging.root.setLevel(dj_settings.LOG_LEVEL)

    if dj_settings.DEBUG:
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(dj_settings.CONSOLE_LOG_FORMAT))
        logging.root.addHandler(console_handler)


def main():
    __initialize_logger()
    logging.info('Initialization complete.')
