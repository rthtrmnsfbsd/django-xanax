# -*- coding: utf-8 -*-
from distutils.core import setup


setup(
    name='django-xanax',
    version='0.1.0',
    author='Vishnevski Alexey',
    author_email='vishnevski.a@gmail.com',
    packages=['xanax',],
    url='http://pypi.python.org/pypi/django-xanax/',
    license='LICENSE',
    description='Django-xanax is a preview and publish interface for django admin application.',
    long_description=open('README.txt').read(),
    install_requires=[
        "Django >= 1.4.0",
        ],
)
