# -*- coding: utf-8 -*-
import logging
from functools import update_wrapper

from django.forms.formsets import all_valid
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.util import unquote

from django.views.decorators.csrf import csrf_protect

from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse

from django.http import Http404
from django.template.response import  TemplateResponse

from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_unicode
from django.utils.crypto import get_random_string
from django_xanax.xanax.settings import GET_SETTING
from django.contrib.admin import widgets, helpers

LOGGER = logging.getLogger(__name__)
csrf_protect_m = method_decorator(csrf_protect)

class PreviewRelatedManager(object):
    def __init__(self, list):
        self.list = list

    def all(self):
        return self.list

class XanaxAdmin(admin.ModelAdmin):
    object_preview_template = None

    def get_list_display(self, request):
        result = super(XanaxAdmin, self).get_list_display(request)
        if not 'preview_link' in result:
            result +=  ('preview_link',)
        return result

    def preview_link(self, obj):
        info = obj._meta.app_label, obj._meta.module_name
        url = reverse('admin:%s_%s_preview' % info, args=(obj.id,))
        return '<a href="%s">preview</a>' % url
    preview_link.allow_tags = True
    preview_link.short_description = 'Preview'


    def has_preview_permission(self, request, obj=None):
        LOGGER.debug('has_preview_permission  True')
        opts = self.opts
        #return request.user.has_perm(opts.app_label + '.' + opts.get_change_permission())
        return True

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

    #TODO: add security decorators
    def add_view(self, request, form_url='', extra_context=None):
        LOGGER.debug('add_view')
        if request.method == 'POST':
            if request.session.get('admin_preview', False):
                obj = self.get_add_view_object(request)
                if obj:
                    preview_token = get_random_string(
                        GET_SETTING('XANAX_PREVIEW_TOKEN_LENGTH')
                    )
                    request.session['preview_POST_%s' % preview_token] = request.POST.copy()
                    request.session['admin_preview'] = False
                    #LOGGER.debug("request.session['preview_POST_%s'] - record POST data"  %  preview_token)
                    return self.preview_view(request, None, preview_token=preview_token, object=obj)
            else:
                preview_token = request.POST.get('preview_token')
                preview_POST = request.session.get('preview_POST_%s' % preview_token)
                #LOGGER.debug("request.session['preview_POST_%s'] - read POST data"  %  preview_token)
                if preview_POST:
                    preview_POST.update(request.POST)
                    request.POST = preview_POST
                    del request.session['preview_POST_%s' % preview_token]
                    if request.POST.get('_back', None):
                        request.session['admin_preview'] = True
                        return self.add_preview_back(request, None, form_url, extra_context)
                    del request.session['admin_preview']
        else:
            request.session['admin_preview'] = True
        return super(XanaxAdmin, self).add_view(request, form_url, extra_context)

    def get_add_view_object(self, request):
        formsets = []
        ModelForm = self.get_form(request)
        form = ModelForm(request.POST, request.FILES)
        inline_instances = self.get_inline_instances(request)
        if form.is_valid():
            new_object = self.save_form(request, form, change=False)
            #FIXME NAGOVNOKOJENO
            cleaned_data = form.cleaned_data
            for f in new_object._meta.many_to_many:
                if f.name in cleaned_data:
                    setattr(new_object, 'pk', 0)
                    setattr(new_object, f.name, cleaned_data[f.name])

        else:
            return None
        prefixes = {}
        for FormSet, inline in zip(self.get_formsets(request), inline_instances):
            prefix = FormSet.get_default_prefix()
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
            if prefixes[prefix] != 1 or not prefix:
                prefix = "%s-%s" % (prefix, prefixes[prefix])
            formset = FormSet(data=request.POST, files=request.FILES,
                instance=new_object,
                save_as_new="_saveasnew" in request.POST,
                prefix=prefix, queryset=inline.queryset(request))
            formsets.append(formset)
        return new_object

    def add_preview_back(self, request, form_url='', extra_context=None):
        "The 'add' admin view for this model."
        model = self.model
        opts = model._meta

        if not self.has_add_permission(request):
            raise PermissionDenied

        ModelForm = self.get_form(request)
        formsets = []
        inline_instances = self.get_inline_instances(request)
        form = ModelForm(request.POST, request.FILES)
        if form.is_valid():
            new_object = self.save_form(request, form, change=False)
        else:
            new_object = self.model()
        prefixes = {}
        for FormSet, inline in zip(self.get_formsets(request), inline_instances):
            prefix = FormSet.get_default_prefix()
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
            if prefixes[prefix] != 1 or not prefix:
                prefix = "%s-%s" % (prefix, prefixes[prefix])
            formset = FormSet(data=request.POST, files=request.FILES,
                instance=new_object,
                save_as_new="_saveasnew" in request.POST,
                prefix=prefix, queryset=inline.queryset(request))
            formsets.append(formset)

        adminForm = helpers.AdminForm(form, list(self.get_fieldsets(request)),
            self.get_prepopulated_fields(request),
            self.get_readonly_fields(request),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request))
            readonly = list(inline.get_readonly_fields(request))
            prepopulated = dict(inline.get_prepopulated_fields(request))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset,
                fieldsets, prepopulated, readonly, model_admin=self)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'title': _('Add %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'is_popup': "_popup" in request.REQUEST,
            'show_delete': False,
            'media': media,
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'app_label': opts.app_label,
            }
        context.update(extra_context or {})
        return self.render_change_form(request, context, form_url=form_url, add=True)


    # TODO: add security decorators
    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.method == 'POST':
            if request.session.get('admin_preview', False):
                obj = self.get_change_view_object(request, object_id)
                if obj:
                    preview_token = get_random_string(
                        GET_SETTING('XANAX_PREVIEW_TOKEN_LENGTH')
                    )
                    request.session['preview_POST_%s' % preview_token] = request.POST.copy()
                    #LOGGER.debug("request.session['preview_POST_%s'] - record POST data"  %  preview_token)
                    request.session['admin_preview'] = False
                    return self.preview_view(request, None, preview_token=preview_token, object=obj)
            else:
                preview_token = request.POST.get('preview_token')
                preview_POST = request.session.get('preview_POST_%s' % preview_token)
                if preview_POST:
                    preview_POST.update(request.POST)
                    request.POST = preview_POST
                    del request.session['preview_POST_%s' % preview_token]
                    if request.POST.get('_back', None):
                        request.session['admin_preview'] = True
                        return self.change_preview_back(request, object_id, form_url, extra_context)
                    del request.session['admin_preview']
        else:
            request.session['admin_preview'] = True
        return super(XanaxAdmin, self).change_view(request, object_id, form_url, extra_context)


    def get_change_view_object(self, request, object_id=None):
        model = self.model
        opts = model._meta
        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})
        #FIXME is it possible to use _saveasnew?
        if request.method == 'POST' and "_saveasnew" in request.POST:
            return self.add_view(request, form_url=reverse('admin:%s_%s_add' %
                                                           (opts.app_label, opts.module_name),
                current_app=self.admin_site.name))

        ModelForm = self.get_form(request, obj)
        formsets = []
        inline_instances = self.get_inline_instances(request)

        form = ModelForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            new_object = self.save_form(request, form, change=True)
        else:
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
        return new_object

    @csrf_protect_m
    def change_preview_back(self, request, object_id, form_url='', extra_context=None):
        "The 'change' admin view for this model."
        model = self.model
        opts = model._meta

        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})

        if request.method == 'POST' and "_saveasnew" in request.POST:
            return self.add_view(request, form_url=reverse('admin:%s_%s_add' %
                                                           (opts.app_label, opts.module_name),
                current_app=self.admin_site.name))

        ModelForm = self.get_form(request, obj)
        formsets = []
        inline_instances = self.get_inline_instances(request)
        form = ModelForm(request.POST, request.FILES, instance=obj)
        prefixes = {}
        for FormSet, inline in zip(self.get_formsets(request, obj), inline_instances):
            prefix = FormSet.get_default_prefix()
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
            if prefixes[prefix] != 1 or not prefix:
                prefix = "%s-%s" % (prefix, prefixes[prefix])
            formset = FormSet(request.POST, request.FILES,
                instance=obj, prefix=prefix,
                queryset=inline.queryset(request))
            formsets.append(formset)

        adminForm = helpers.AdminForm(form, self.get_fieldsets(request, obj),
            self.get_prepopulated_fields(request, obj),
            self.get_readonly_fields(request, obj),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            readonly = list(inline.get_readonly_fields(request, obj))
            prepopulated = dict(inline.get_prepopulated_fields(request, obj))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset,
                fieldsets, prepopulated, readonly, model_admin=self)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'title': _('Change %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'object_id': object_id,
            'original': obj,
            'is_popup': "_popup" in request.REQUEST,
            'media': media,
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'app_label': opts.app_label,
            }
        context.update(extra_context or {})
        return self.render_change_form(request, context, change=True, obj=obj, form_url=form_url)




    # TODO: add security decorators
    # TODO: add preview form and submit row
    # TODO: add preview content
    def preview_view(self, request, object_id=None,
                     extra_context=None, preview_token=None, object=None):
        model = self.model
        opts = model._meta

        if request.method == 'GET':
            object = self.get_object(request, unquote(object_id))
        if object is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})


        context = {
            'is_post': bool(request.method == 'POST'),
            'action_list': [],
            'module_name': capfirst(force_unicode(opts.verbose_name_plural)),
            'object': object,
            'app_label':  opts.app_label,
            'opts': opts,
            'title': _('Change %s') % force_unicode(opts.verbose_name),
            'adminform': '',
            'object_id': object_id,
            'original': object,
            'is_popup': "_popup" in request.REQUEST,
            'media': '',
            'inline_admin_formsets': '',
            'errors':[],
            'add': False,
            'change': True,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request, object),
            'has_delete_permission': self.has_delete_permission(request, object),
            'has_file_field': True, # FIXME - this should check if form or formsets have a FileField,
            'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
            'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'save_as': self.save_as,
            'save_on_top': self.save_on_top,
            'preview_token': preview_token,
            'is_admin_preview': True,
            'object_publish':False,
            }


        #TODO remove jQuery


        return TemplateResponse(request, self.object_preview_template or [
            "admin/%s/%s/object_preview.html" % ( opts.app_label, opts.object_name.lower()),
            "admin/%s/object_preview.html" %  opts.app_label,
            "admin/object_preview.html"
        ], context, current_app=self.admin_site.name)



