===========
Django Xanax
===========
Reduces anxiety and worry, helps normalize sleeping.

Django-xanax is a preview interface for django admin application.

HOWTO:

#admin.py
from xanax import XanaxAdmin
class MyModelAdmin(XanaxAdmin):
    #your code here
     def preview_context_handler(self, context):
            ''' Customise your preview context here.'''
            return  context


#templates/my_app/my_model/object_preview.html
{% extends 'my_base.html' %}
{{ object }}
{{ object.attr_1 }}
{{ iniline_objects.my_inline.0.attr_1 }}


#grappelli
see https://github.com/vishnevski/django-xanax-grappelli


#bootstrap
see https://github.com/vishnevski/django-xanax-bootstrap

