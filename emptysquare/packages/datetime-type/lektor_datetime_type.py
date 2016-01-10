# -*- coding: utf-8 -*-
from datetime import datetime

from lektor.pluginsystem import Plugin
from lektor.types import Type


class DatetimeType(Type):
    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing date')
        try:
            return datetime.strptime(raw.value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return raw.bad_value('Bad datetime format')


def strftime_filter(dt, fmt='%B %-d, %Y'):
    if isinstance(dt, datetime):
        return dt.strftime(fmt)

    return ''


class DatetimeTypePlugin(Plugin):
    name = u'datetime type'
    description = u'Adds a new field type, "datetime".'

    def on_setup_env(self, **extra):
        self.env.types['datetime'] = DatetimeType
        self.env.jinja_env.filters['strftime'] = strftime_filter
