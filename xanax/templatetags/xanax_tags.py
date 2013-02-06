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