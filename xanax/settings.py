# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


XANAX_FORSED_PREVIEW = getattr(settings, 'XANAX_FORSED_PREVIEW', False)
XANAX_LIST_DISPLAY = getattr(settings, 'XANAX_LIST_DISPLAY', False)
XANAX_PREVIEW_BUTTON = getattr(settings, 'XANAX_PREVIEW_BUTTON', False)
XANAX_USE_PUBLISH = getattr(settings, 'XANAX_USE_PUBLISH', False)
XANAX_PREVIEW_TOKEN_LENGTH = getattr(settings, 'XANAX_USE_PUBLISH', 32)


def get_setting(name):
    import settings
    try:
        from constance import config
    except ImportError:
        return getattr(settings, name, None)
    return getattr(config, name, getattr(settings, name, None))

GET_SETTING = getattr(settings, 'GET_SETTING', get_setting)