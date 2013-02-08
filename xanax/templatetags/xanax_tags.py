# -*- coding: utf-8 -*-
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

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
    opts = context['opts']
    change = context['change']
    is_popup = context['is_popup']
    save_as = context['save_as']

    context.update({
        'onclick_attrib': (opts.get_ordered_objects() and change
                           and 'onclick="submitOrderForm();"' or ''),
        'show_delete_link': (not is_popup and context['has_delete_permission']
                             and (change or context['show_delete'])),
        'show_save_as_new': not is_popup and change and save_as,
        'show_save_and_add_another': context['has_add_permission'] and
                                     not is_popup and (not save_as or context['add']),
        'show_save_and_continue': not is_popup and context['has_change_permission'],
        'is_popup': is_popup,
        'show_save': True,
        })
    return context
