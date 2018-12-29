from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Submit
from django import forms

from YtManagerApp.dynamic_preferences_registry import MarkDeletedAsWatched, AutoDeleteWatched, AutoDownloadEnabled, \
    DownloadGlobalLimit, DownloadGlobalSizeLimit, DownloadSubscriptionLimit, DownloadMaxAttempts, DownloadOrder, \
    DownloadPath, DownloadFilePattern, DownloadFormat, DownloadSubtitles, DownloadAutogeneratedSubtitles, \
    DownloadAllSubtitles, DownloadSubtitlesLangs, DownloadSubtitlesFormat
from YtManagerApp.management.appconfig import appconfig
from YtManagerApp.models import VIDEO_ORDER_CHOICES


class SettingsForm(forms.Form):

    mark_deleted_as_watched = forms.BooleanField(
        help_text='When a downloaded video is deleted from the system, it will be marked as \'watched\'.',
        initial=MarkDeletedAsWatched.default,
        required=False
    )

    automatically_delete_watched = forms.BooleanField(
        help_text='Videos marked as watched are automatically deleted.',
        initial=AutoDeleteWatched.default,
        required=False
    )

    auto_download = forms.BooleanField(
        help_text='Enables or disables automatic downloading.',
        initial=AutoDownloadEnabled.default,
        required=False
    )

    download_global_limit = forms.IntegerField(
        help_text='Limits the total number of videos downloaded (-1/unset = no limit).',
        initial=DownloadGlobalLimit.default,
        required=False
    )

    download_global_size_limit = forms.IntegerField(
        help_text='Limits the total amount of space used in MB (-1/unset = no limit).',
        initial=DownloadGlobalSizeLimit.default,
        required=False
    )

    download_subscription_limit = forms.IntegerField(
        help_text='Limits the number of videos downloaded per subscription (-1/unset = no limit). '
                  ' This setting can be overriden for each individual subscription in the subscription edit dialog.',
        initial=DownloadSubscriptionLimit.default,
        required=False
    )

    max_download_attempts = forms.IntegerField(
        help_text='How many times to attempt downloading a video until giving up.',
        initial=DownloadMaxAttempts.default,
        min_value=1,
        required=True
    )

    download_order = forms.ChoiceField(
        help_text='The order in which videos will be downloaded.',
        choices=VIDEO_ORDER_CHOICES,
        initial=DownloadOrder.default,
        required=True
    )

    download_path = forms.CharField(
        help_text='Path on the disk where downloaded videos are stored. '
                  'You can use environment variables using syntax: <code>${env:...}</code>',
        initial=DownloadPath.default,
        max_length=1024,
        required=True
    )

    download_file_pattern = forms.CharField(
        help_text='A pattern which describes how downloaded files are organized. Extensions are automatically appended.'
                  ' You can use the following fields, using the <code>${field}</code> syntax:'
                  ' channel, channel_id, playlist, playlist_id, playlist_index, title, id.'
                  ' Example: <code>${channel}/${playlist}/S01E${playlist_index} - ${title} [${id}]</code>',
        initial=DownloadFilePattern.default,
        max_length=1024,
        required=True
    )

    download_format = forms.CharField(
        help_text='Download format that will be passed to youtube-dl. '
                  ' See the <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#format-selection">'
                  ' youtube-dl documentation</a> for more details.',
        initial=DownloadFormat.default,
        required=True
    )

    download_subtitles = forms.BooleanField(
        help_text='Enable downloading subtitles for the videos.'
                  ' The flag is passed directly to youtube-dl. You can find more information'
                  ' <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#subtitle-options">here</a>.',
        initial=DownloadSubtitles.default,
        required=False
    )

    download_autogenerated_subtitles = forms.BooleanField(
        help_text='Enables downloading the automatically generated subtitle.'
                  ' The flag is passed directly to youtube-dl. You can find more information'
                  ' <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#subtitle-options">here</a>.',
        initial=DownloadAutogeneratedSubtitles.default,
        required=False
    )

    download_subtitles_all = forms.BooleanField(
        help_text='If enabled, all the subtitles in all the available languages will be downloaded.'
                  ' The flag is passed directly to youtube-dl. You can find more information'
                  ' <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#subtitle-options">here</a>.',
        initial=DownloadAllSubtitles.default,
        required=False
    )

    download_subtitles_langs = forms.CharField(
        help_text='Comma separated list of languages for which subtitles will be downloaded.'
                  ' The flag is passed directly to youtube-dl. You can find more information'
                  ' <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#subtitle-options">here</a>.',
        initial=DownloadSubtitlesLangs.default,
        required=False
    )

    download_subtitles_format = forms.CharField(
        help_text='Subtitles format preference. Examples: srt/ass/best'
                  ' The flag is passed directly to youtube-dl. You can find more information'
                  ' <a href="https://github.com/rg3/youtube-dl/blob/master/README.md#subtitle-options">here</a>.',
        initial=DownloadSubtitlesFormat.default,
        required=False
    )

    ALL_PROPS = [
        'mark_deleted_as_watched',
        'automatically_delete_watched',

        'auto_download',
        'download_path',
        'download_file_pattern',
        'download_format',
        'download_order',
        'download_global_limit',
        'download_global_size_limit',
        'download_subscription_limit',
        'max_download_attempts',

        'download_subtitles',
        'download_subtitles_langs',
        'download_subtitles_all',
        'download_autogenerated_subtitles',
        'download_subtitles_format',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-6'
        self.helper.field_class = 'col-lg-6'
        self.helper.layout = Layout(
            'mark_deleted_as_watched',
            'automatically_delete_watched',
            HTML('<h2>Download settings</h2>'),
            'auto_download',
            'download_path',
            'download_file_pattern',
            'download_format',
            'download_order',
            'download_global_limit',
            'download_global_size_limit',
            'download_subscription_limit',
            'max_download_attempts',
            HTML('<h2>Subtitles download settings</h2>'),
            'download_subtitles',
            'download_subtitles_langs',
            'download_subtitles_all',
            'download_autogenerated_subtitles',
            'download_subtitles_format',
            Submit('submit', value='Save')
        )

    @staticmethod
    def get_initials(user):
        return {
            x: user.preferences[x] for x in SettingsForm.ALL_PROPS
        }

    def save(self, user):
        for prop in SettingsForm.ALL_PROPS:
            user.preferences[prop] = self.cleaned_data[prop]


class AdminSettingsForm(forms.Form):

    api_key = forms.CharField(label="YouTube API key")

    allow_registrations = forms.BooleanField(
        label="Allow user registrations",
        help_text="Disabling this option will prevent anyone from registering to the site.",
        initial=True,
        required=False
    )

    sync_schedule = forms.CharField(
        label="Synchronization schedule",
        help_text="How often should the application look for new videos.",
        initial="5 * * * *",
        required=True
    )

    scheduler_concurrency = forms.IntegerField(
        label="Synchronization concurrency",
        help_text="How many jobs are executed executed in parallel. Since most jobs are I/O bound (mostly use the hard "
                  "drive and network), there is no significant advantage to increase it.",
        initial=2,
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'
        self.helper.layout = Layout(
            HTML('<h2>General settings</h2>'),
            'api_key',
            'allow_registrations',
            HTML('<h2>Scheduler settings</h2>'),
            'sync_schedule',
            'scheduler_concurrency',
            Submit('submit', value='Save')
        )

    @staticmethod
    def get_initials():
        return {
            'api_key': appconfig.youtube_api_key,
            'allow_registrations': appconfig.allow_registrations,
            'sync_schedule': appconfig.sync_schedule,
            'scheduler_concurrency': appconfig.concurrency,
        }

    def save(self):
        api_key = self.cleaned_data['api_key']
        if api_key is not None and len(api_key) > 0:
            appconfig.youtube_api_key = api_key

        allow_registrations = self.cleaned_data['allow_registrations']
        if allow_registrations is not None:
            appconfig.allow_registrations = allow_registrations

        sync_schedule = self.cleaned_data['sync_schedule']
        if sync_schedule is not None and len(sync_schedule) > 0:
            appconfig.sync_schedule = sync_schedule

        concurrency = self.cleaned_data['scheduler_concurrency']
        if concurrency is not None:
            appconfig.concurrency = concurrency
