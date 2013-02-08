# -*- coding: utf-8 -*-
import logging
from functools import update_wrapper

from django.forms.formsets import all_valid
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.util import unquote

from django.views.decorators.csrf import csrf_protect

from django.core.exceptions import PermissionDenied

from django.http import Http404
from django.template.response import  TemplateResponse

from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode
from django.utils.crypto import get_random_string
from django_xanax.xanax.settings import GET_SETTING


LOGGER = logging.getLogger(__name__)

csrf_protect_m = method_decorator(csrf_protect)

class XanaxAdmin(admin.ModelAdmin):

    object_preview_template = None

    def __init__(self, *args, **kwargs):
        super(XanaxAdmin, self).__init__(*args, **kwargs)

    def get_urls(self):
        from django.conf.urls import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name
        urlpatterns = super(XanaxAdmin, self).get_urls()

        admin_preview_url = patterns('',
            url(r'^(.+)/preview/$',
            wrap(self.preview_view),
            name='%s_%s_preview' % info),
        )
        return admin_preview_url + urlpatterns

    def get_preview_object(self, request, object_id=None):

        LOGGER.debug('get_preview_object')

        #TODO: "_saveasnew" in request.POST:
        model = self.model
        opts = model._meta

        obj = None
        if object_id:
            obj = self.get_object(request, unquote(object_id))
            #LOGGER.debug('get_preview_object id %s, obj %s' % (object_id, obj))

        if request.session.get('admin_preview', False)\
            and request.method == 'POST':
            #LOGGER.debug('get_preview_object admin_preview True')
            ModelForm = self.get_form(request, obj)
            formsets = []
            inline_instances = self.get_inline_instances(request)
            form = ModelForm(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                request.session['admin_preview'] = False
                form_validated = True
                new_object = self.save_form(request, form, change=True)
            else:
                #LOGGER.debug('get_preview_object form is not valid')
                return None

            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request, new_object), inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1 or not prefix:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(request.POST, request.FILES,
                    instance=new_object, prefix=prefix,
                    queryset=inline.queryset(request))

                formsets.append(formset)

            if all_valid(formsets) and form_validated:
                return new_object

        if obj is None:
            raise Http404(
                _('%(name)s object with primary key %(key)r does not exist.')
                % {'name': force_unicode(opts.verbose_name),
                   'key': escape(object_id)})
        if not self.has_preview_permission(request, obj):
            raise PermissionDenied

        return obj

    def generate_preview_token(self):
        return get_random_string(GET_SETTING('XANAX_PREVIEW_TOKEN_LENGTH'))


    # TODO: add security decorators
    def change_view(self, request, object_id, form_url='', extra_context=None):
        LOGGER.debug('change_view')

        if request.method == 'GET':
            request.session['admin_preview'] = True

        if request.method == 'POST':

            if request.session.get('admin_preview', False):
                preview_token = self.generate_preview_token()
                request.session['preview_POST_%s' % preview_token] = request.POST.copy()
                #LOGGER.debug("request.session['preview_POST_%s'] - record POST data"  %  preview_token)
                return self.preview_view(request, object_id, preview_token=preview_token)

            else:
                preview_token = request.POST.get('preview_token')
                preview_POST = request.session.get('preview_POST_%s' % preview_token)
                #LOGGER.debug("request.session['preview_POST_%s'] - read POST data"  %  preview_token)
                if preview_POST:
                    request.POST = preview_POST
                    del request.session['admin_preview']
                    del request.session['preview_POST_%s' % preview_token]
                return super(XanaxAdmin, self).change_view(request, object_id, form_url, extra_context)

        return super(XanaxAdmin, self).change_view(request, object_id, form_url, extra_context)


    def has_preview_permission(self, request, obj=None):
        LOGGER.debug('has_preview_permission  True')
        opts = self.opts
        #return request.user.has_perm(opts.app_label + '.' + opts.get_change_permission())
        return True


    # TODO: add security decorators
    # TODO: add preview form and submit row
    # TODO: add preview content
    def preview_view(self, request, object_id=None, extra_context=None, preview_token=None):
        preview_action = ''
        LOGGER.debug('preview_view')
        if request.method == 'GET':
            preview_action = '../'
        obj = self.get_preview_object(request, object_id)

        if not obj:
            del request.session['preview_POST_%s' % preview_token]
            return super(XanaxAdmin, self).change_view(request, object_id)

        model = self.model
        opts = model._meta

        #TODO remove jQuery

        context = {
            'action_list': [],
            'module_name': capfirst(force_unicode(opts.verbose_name_plural)),
            'object': obj,
            'app_label':  opts.app_label,
            'opts': opts,
            'title': _('Change %s') % force_unicode(opts.verbose_name),
            'adminform': '',
            'object_id': object_id,
            'original': obj,
            'is_popup': "_popup" in request.REQUEST,
            'media': '',
            'inline_admin_formsets': '',
            'errors':[],
            'preview_action': preview_action,
            'add': False,
            'change': True,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request, obj),
            'has_delete_permission': self.has_delete_permission(request, obj),
            'has_file_field': True, # FIXME - this should check if form or formsets have a FileField,
            'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
            'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'save_as': self.save_as,
            'save_on_top': self.save_on_top,
            'preview_token': preview_token,
            'is_admin_preview': True,
            }
        return TemplateResponse(request, self.object_preview_template or [
            "admin/%s/%s/object_preview.html" % ( opts.app_label, opts.object_name.lower()),
            "admin/%s/object_preview.html" %  opts.app_label,
            "admin/object_preview.html"
        ], context, current_app=self.admin_site.name)



