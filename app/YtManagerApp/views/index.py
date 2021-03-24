from math import log, floor

import importlib
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import CreateView, UpdateView, DeleteView, FormView
from django.views.generic.edit import FormMixin
from django.conf import settings
from django.core.paginator import Paginator

from YtManagerApp.IProvider import IProvider
from YtManagerApp.management.videos import get_videos
from YtManagerApp.management.appconfig import appconfig
from YtManagerApp.models import Subscription, SubscriptionFolder, VIDEO_ORDER_CHOICES, VIDEO_ORDER_MAPPING
from YtManagerApp.utils import subscription_file_parser
from YtManagerApp.views.controls.modal import ModalMixin

import logging
import datetime


class VideoFilterForm(forms.Form):
    CHOICES_SHOW_WATCHED = (
        ('y', 'Watched'),
        ('n', 'Not watched'),
        ('all', '(All)')
    )

    CHOICES_SHOW_DOWNLOADED = (
        ('y', 'Downloaded'),
        ('n', 'Not downloaded'),
        ('all', '(All)')
    )

    MAPPING_SHOW = {
        'y': True,
        'n': False,
        'all': None
    }

    CHOICES_RESULT_COUNT = (
        (25, 25),
        (50, 50),
        (100, 100),
        (200, 200)
    )

    query = forms.CharField(label='', required=False)
    sort = forms.ChoiceField(label='Sort:', choices=VIDEO_ORDER_CHOICES, initial='oldest')
    show_watched = forms.ChoiceField(label='Show only: ', choices=CHOICES_SHOW_WATCHED, initial='n')
    show_downloaded = forms.ChoiceField(label='', choices=CHOICES_SHOW_DOWNLOADED, initial='all')
    subscription_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    folder_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    page = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    results_per_page = forms.ChoiceField(label='Results per page: ', choices=CHOICES_RESULT_COUNT, initial=50)

    def __init__(self, data=None):
        super().__init__(data, auto_id='form_video_filter_%s')
        self.helper = FormHelper()
        self.helper.form_id = 'form_video_filter'
        self.helper.form_class = 'form-inline'
        self.helper.form_method = 'POST'
        self.helper.form_action = 'ajax_get_videos'
        self.helper.field_class = 'mr-1'
        self.helper.label_class = 'ml-2 mr-1 no-asterisk'

        self.helper.layout = Layout(
            Field('query', placeholder='Search'),
            'sort',
            'show_watched',
            'show_downloaded',
            'subscription_id',
            'folder_id',
            'page',
            'results_per_page'
        )

    def clean_sort(self):
        data = self.cleaned_data['sort']
        return VIDEO_ORDER_MAPPING[data]

    def clean_show_downloaded(self):
        data = self.cleaned_data['show_downloaded']
        return VideoFilterForm.MAPPING_SHOW[data]

    def clean_show_watched(self):
        data = self.cleaned_data['show_watched']
        return VideoFilterForm.MAPPING_SHOW[data]


def __tree_folder_id(fd_id):
    if fd_id is None:
        return '#'
    return 'folder' + str(fd_id)


def __tree_sub_id(sub_id):
    if sub_id is None:
        return '#'
    return 'sub' + str(sub_id)


def index(request: HttpRequest):

    if not appconfig.initialized:
        return redirect('first_time_0')

    context = {
        'config_errors': settings.CONFIG_ERRORS,
        'config_warnings': settings.CONFIG_WARNINGS,
    }
    if request.user.is_authenticated:
        context.update({
            'filter_form': VideoFilterForm(),
        })
        return render(request, 'YtManagerApp/index.html', context)
    else:
        return render(request, 'YtManagerApp/index_unauthenticated.html', context)


@login_required
def ajax_get_tree(request: HttpRequest):
    def human_format(number):
        units = ['', 'K', 'M', 'G', 'T', 'P']
        k = 1000.0
        magnitude = int(floor(log(number, k)))
        if magnitude > 0:
            return '{0:.2}{1:s}'.format(number / k**magnitude, units[magnitude])
        else:
            return '{0}'.format(number)

    def visit(node):
        if isinstance(node, SubscriptionFolder):
            unwatched = node.get_unwatched_count()
            return {
                "id": __tree_folder_id(node.id),
                "text": node.name,
                "type": "folder",
                "state": {"opened": True},
                "parent": __tree_folder_id(node.parent_id),
                "li_attr": {"data-unwatched-count": unwatched}
            }
        elif isinstance(node, Subscription):
            unwatched = node.get_unwatched_count()
            return {
                "id": __tree_sub_id(node.id),
                "type": "sub",
                "text": node.name,
                "icon": node.thumb.url,
                "parent": __tree_folder_id(node.parent_folder_id),
                "li_attr": {"data-unwatched-count": unwatched}
            }

    result = SubscriptionFolder.traverse(None, request.user, visit)
    return JsonResponse(result, safe=False)


@login_required
def ajax_get_videos(request: HttpRequest):
    if request.method == 'POST':
        form = VideoFilterForm(request.POST)
        if form.is_valid():
            videos = get_videos(
                user=request.user,
                sort_order=form.cleaned_data['sort'],
                query=form.cleaned_data['query'],
                subscription_id=form.cleaned_data['subscription_id'],
                folder_id=form.cleaned_data['folder_id'],
                only_watched=form.cleaned_data['show_watched'],
                only_downloaded=form.cleaned_data['show_downloaded']
            )

            duration_raw = videos.aggregate(Sum('duration'))['duration__sum'] or 0
            duration = str(datetime.timedelta(seconds=duration_raw))

            paginator = Paginator(videos, form.cleaned_data['results_per_page'])
            videos = paginator.get_page(form.cleaned_data['page'])

            context = {
                'videos': videos,
                'duration': duration
            }

            return render(request, 'YtManagerApp/index_videos.html', context)

    return HttpResponseBadRequest()


class SubscriptionFolderForm(forms.ModelForm):
    class Meta:
        model = SubscriptionFolder
        fields = ['name', 'parent']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean_name(self):
        name = self.cleaned_data['name']
        return name.strip()

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        parent = cleaned_data.get('parent')

        # Check name is unique in parent folder
        args_id = []
        if self.instance is not None:
            args_id.append(~Q(id=self.instance.id))

        if SubscriptionFolder.objects.filter(parent=parent, name__iexact=name, *args_id).count() > 0:
            raise forms.ValidationError(
                'A folder with the same name already exists in the given parent directory!', code='already_exists')

        # Check for cycles
        if self.instance is not None:
            self.__test_cycles(parent)

    def __test_cycles(self, new_parent):
        visited = [self.instance.id]
        current = new_parent
        while current is not None:
            if current.id in visited:
                raise forms.ValidationError('Selected parent would create a parenting cycle!', code='parenting_cycle')
            visited.append(current.id)
            current = current.parent


class CreateFolderModal(LoginRequiredMixin, ModalMixin, CreateView):
    template_name = 'YtManagerApp/controls/folder_create_modal.html'
    form_class = SubscriptionFolderForm

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class UpdateFolderModal(LoginRequiredMixin, ModalMixin, UpdateView):
    template_name = 'YtManagerApp/controls/folder_update_modal.html'
    model = SubscriptionFolder
    form_class = SubscriptionFolderForm


class DeleteFolderForm(forms.Form):
    keep_subscriptions = forms.BooleanField(required=False, initial=False, label="Keep subscriptions")


class DeleteFolderModal(LoginRequiredMixin, ModalMixin, FormMixin, DeleteView):
    template_name = 'YtManagerApp/controls/folder_delete_modal.html'
    model = SubscriptionFolder
    form_class = DeleteFolderForm

    def __init__(self, *args, **kwargs):
        self.object = None
        super().__init__(*args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object.delete_folder(keep_subscriptions=form.cleaned_data['keep_subscriptions'])
        return super().form_valid(form)


class CreateSubscriptionForm(forms.ModelForm):
    playlist_url = forms.URLField(label='Playlist/Channel URL')

    class Meta:
        model = Subscription
        fields = ['parent_folder', 'auto_download',
                  'download_limit', 'download_order', "automatically_delete_watched"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'playlist_url',
            'parent_folder',
            HTML('<hr>'),
            HTML('<h5>Download configuration overloads</h5>'),
            'auto_download',
            'download_limit',
            'download_order',
            'automatically_delete_watched'
        )

    def save(self, commit=True):
        m: Subscription = super(CreateSubscriptionForm, self).save(commit=False)

        for provider_name in settings.INSTALLED_PROVIDERS:
            provider: IProvider = importlib.import_module(provider_name+".jobs").Jobs
            if provider.is_url_valid_for_module(self.cleaned_data['playlist_url']):
                provider.process_url(self.cleaned_data['playlist_url'], m)
                m.provider = provider_name
                break

        if commit:
            m.save()

        return m

    def clean_playlist_url(self):
        found_provider = False
        try:
            for provider_name in settings.INSTALLED_PROVIDERS:
                provider: IProvider = importlib.import_module(provider_name+".jobs").Jobs
                if provider.is_url_valid_for_module(self.cleaned_data['playlist_url']):
                    found_provider = True
                    break
        except Exception as e:
            raise forms.ValidationError(str(e))
        if not found_provider:
            raise forms.ValidationError("URL not recognused. Please verify that the URL is correct")

        return self.cleaned_data['playlist_url']


class CreateSubscriptionModal(LoginRequiredMixin, ModalMixin, CreateView):
    template_name = 'YtManagerApp/controls/subscription_create_modal.html'
    form_class = CreateSubscriptionForm

    def form_valid(self, form):
        form.instance.user = self.request.user
        found_provider = False
        try:
            for provider_name in settings.INSTALLED_PROVIDERS:
                provider: IProvider = importlib.import_module(provider_name+".jobs").Jobs
                if provider.is_url_valid_for_module(form.cleaned_data['playlist_url']):
                    found_provider = True
                    break
        except Exception as e:
            return self.modal_response(form, False, str(e))
        if not found_provider:
            return self.modal_response(form, False, "URL not recognused. Please verify that the URL is correct")

        return super().form_valid(form)


class UpdateSubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['name', 'parent_folder', 'auto_download',
                  'download_limit', 'download_order', "automatically_delete_watched", 'last_synchronised']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'name',
            'parent_folder',
            HTML('<hr>'),
            HTML('<h5>Download configuration overloads</h5>'),
            'auto_download',
            'download_limit',
            'download_order',
            'automatically_delete_watched',
            Field('last_synchronised', readonly=True)
        )


class UpdateSubscriptionModal(LoginRequiredMixin, ModalMixin, UpdateView):
    template_name = 'YtManagerApp/controls/subscription_update_modal.html'
    model = Subscription
    form_class = UpdateSubscriptionForm


class DeleteSubscriptionForm(forms.Form):
    keep_downloaded_videos = forms.BooleanField(required=False, initial=False, label="Keep downloaded videos")


class DeleteSubscriptionModal(LoginRequiredMixin, ModalMixin, FormMixin, DeleteView):
    template_name = 'YtManagerApp/controls/subscription_delete_modal.html'
    model = Subscription
    form_class = DeleteSubscriptionForm

    def __init__(self, *args, **kwargs):
        self.object = None
        super().__init__(*args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.object.delete_subscription(keep_downloaded_videos=form.cleaned_data['keep_downloaded_videos'])
        return super().form_valid(form)


class ImportSubscriptionsForm(forms.Form):
    TRUE_FALSE_CHOICES = (
        (None, '(default)'),
        (True, 'Yes'),
        (False, 'No')
    )

    VIDEO_ORDER_CHOICES_WITH_EMPTY = (
        ('', '(default)'),
        *VIDEO_ORDER_CHOICES,
    )

    file = forms.FileField(label='File to import',
                           help_text='Supported file types: OPML, subscription list')
    parent_folder = forms.ModelChoiceField(SubscriptionFolder.objects, required=False)
    auto_download = forms.ChoiceField(choices=TRUE_FALSE_CHOICES, required=False)
    download_limit = forms.IntegerField(required=False)
    download_order = forms.ChoiceField(choices=VIDEO_ORDER_CHOICES_WITH_EMPTY, required=False)
    automatically_delete_watched = forms.ChoiceField(choices=TRUE_FALSE_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'file',
            'parent_folder',
            HTML('<hr>'),
            HTML('<h5>Download configuration overloads</h5>'),
            'auto_download',
            'download_limit',
            'download_order',
            'automatically_delete_watched'
        )

    def __clean_empty_none(self, name: str):
        data = self.cleaned_data[name]
        if isinstance(data, str) and len(data) == 0:
            return None
        return data

    def __clean_boolean(self, name: str):
        data = self.cleaned_data[name]
        if isinstance(data, str) and len(data) == 0:
            return None
        if isinstance(data, str):
            return data == 'True'
        return data

    def clean_auto_download(self):
        return self.__clean_boolean('auto_download')

    def clean_automatically_delete_watched(self):
        return self.__clean_boolean('automatically_delete_watched')

    def clean_download_order(self):
        return self.__clean_empty_none('download_order')


class ImportSubscriptionsModal(LoginRequiredMixin, ModalMixin, FormView):
    template_name = 'YtManagerApp/controls/subscriptions_import_modal.html'
    form_class = ImportSubscriptionsForm

    def form_valid(self, form):
        file = form.cleaned_data['file']

        # Parse file
        try:
            url_list = list(subscription_file_parser.parse(file))
        except subscription_file_parser.FormatNotSupportedError:
            return super().modal_response(form, success=False,
                                          error_msg="The file could not be parsed! "
                                                    "Possible problems: format not supported, file is malformed.")

        print(form.cleaned_data)

        # Create subscriptions
        for url in url_list:
            sub = Subscription()
            sub.user = self.request.user
            sub.parent_folder = form.cleaned_data['parent_folder']
            sub.auto_download = form.cleaned_data['auto_download']
            sub.download_limit = form.cleaned_data['download_limit']
            sub.download_order = form.cleaned_data['download_order']
            sub.automatically_delete_watched = form.cleaned_data["automatically_delete_watched"]
            try:
                for provider_name in settings.INSTALLED_PROVIDERS:
                    provider: IProvider = importlib.import_module(provider_name+".jobs").Jobs
                    if provider.is_url_valid_for_module(url):
                        sub.provider = provider_name
                        provider.process_url(url, sub)
                        break
            except Exception as e:
                logging.error("Import subscription error - error processing URL %s: %s", url, e)
                continue

            sub.save()

        return super().form_valid(form)
