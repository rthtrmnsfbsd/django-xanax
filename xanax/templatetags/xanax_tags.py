# -*- coding: utf-8 -*-
from django import template
from django.utils.safestring import mark_safe

from xanax.settings import GET_SETTING


register = template.Library()

GET_PREVIEW_ACTIONS = {
    'show_back_link' : True,
    'show_edit_link' : True,
    'show_delete_link' : True,
    'show_publish' : True,
    }

POST_PREVIEW_ACTIONS = {
    'show_back' : True,
    'show_publish' : True
}


@register.simple_tag(takes_context=True)
def preview_token(context):
    result = ''
    preview_token = context.get('preview_token')
    if preview_token:
        result = mark_safe(
            u"<div style='display:none'>"
            u"<input type='hidden' name='preview_token' value='%s' />"
            u"</div>"
            % preview_token
        )
    return result

@register.inclusion_tag('admin/xanax/preview_submit_line.html', takes_context=True)
def preview_submit_row(context):
    """
    Displays the row of buttons for delete and save.
    """

    preview_token = context.get('preview_token', None)
    is_admin_preview = context.get('is_admin_preview', None)
    opts = context.get('opts', None)
    change = context.get('change', None)
    is_popup = context.get('is_popup', None)
    save_as = context.get('save_as', None)
    is_post = context.get('is_post', None)
    if preview_token and is_admin_preview:
        context.update({
            'onclick_attrib': (opts.get_ordered_objects() and change
                               and 'onclick="submitOrderForm();"' or ''),
            'show_delete_link': (not is_popup and context['has_delete_permission']
                                and context.get('object_id', False)
                                 and (change or context['show_delete'])),
            'show_save_as_new': not is_popup and change and save_as and is_post,
            'show_save_and_add_another': context['has_add_permission'] and is_post and
                                         not is_popup and (not save_as or context['add']),
            'show_save_and_continue': not is_popup and is_post and context['has_change_permission'],
            'is_popup': is_popup,
            'show_back' : is_post,
            'show_save' : is_post,
            'show_back_link' : not is_post,
            'show_edit_link' : not is_post,
            'show_publish' : not is_post and context['has_add_permission']
                and context['object_publish'] and GET_SETTING('XANAX_USE_PUBLISH'),

            })
    return context
