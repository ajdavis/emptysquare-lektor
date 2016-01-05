# -*- coding: utf-8 -*-
import hashlib
import posixpath
import uuid
from datetime import datetime, date
from functools import partial

import pkg_resources
from lektor.build_programs import BuildProgram
from lektor.db import F
from lektor.environment import Expression
from lektor.pluginsystem import Plugin
from lektor.context import get_ctx, url_to
from lektor.sourceobj import VirtualSourceObject

from werkzeug.contrib.atom import AtomFeed
from markupsafe import escape


class AtomFeedSource(VirtualSourceObject):
    def __init__(self, parent, feed_name, plugin):
        VirtualSourceObject.__init__(self, parent)
        self.plugin = plugin
        self.feed_name = feed_name

    @property
    def path(self):
        return posixpath.join(self.parent.path, self.filename)

    @property
    def url_path(self):
        p = self.plugin.get_atom_config(self.feed_name, 'url_path')
        if p:
            return p

        return posixpath.join(self.parent.url_path, self.filename)

    def __getattr__(self, item):
        try:
            return self.plugin.get_atom_config(self.feed_name, item)
        except KeyError:
            raise AttributeError(item)


def get_id(s):
    return uuid.UUID(bytes=hashlib.md5(s).digest(), version=3).urn


def get_item_title(item, field):
    if field in item:
        return item[field]
    return item.record_label


def get_item_body(item, field):
    if field not in item:
        raise RuntimeError('Body field not found: %r' % field)
    with get_ctx().changed_base_url(item.url_path):
        return unicode(escape(item[field]))


def get_item_updated(item, field):
    if field in item:
        rv = item[field]
    else:
        rv = datetime.utcnow()
    if isinstance(rv, date) and not isinstance(rv, datetime):
        rv = datetime(*rv.timetuple()[:3])
    return rv


class AtomFeedBuilderProgram(BuildProgram):
    def produce_artifacts(self):
        self.declare_artifact(
            self.source.url_path,
            sources=list(self.source.iter_source_filenames()))

    def build_artifact(self, artifact):
        ctx = get_ctx()
        feed_source = self.source
        blog = feed_source.parent

        summary = blog[feed_source.blog_summary_field]
        subtitle_type = ('html' if hasattr(summary, '__html__') else 'text')
        blog_author = unicode(blog[feed_source.item_author_field] or '')
        generator = ('Lektor',
                     'https://www.getlektor.com/',
                     pkg_resources.get_distribution('Lektor').version)

        feed = AtomFeed(
            title=blog[feed_source.item_title_field] or 'Feed',
            subtitle=unicode(summary or ''),
            subtitle_type=subtitle_type,
            author=blog_author,
            feed_url=url_to(feed_source, external=True),
            url=url_to(blog, external=True),
            id=get_id(ctx.env.project.id),
            generator=generator)

        if feed_source.items:
            # "feed_source.items" is a string like "site.query('/blog')".
            expr = Expression(ctx.env, feed_source.items)
            items = expr.evaluate(ctx.pad)
        else:
            items = blog.children

        if feed_source.item_model:
            items = items.filter(F._model == feed_source.item_model)

        order_by = '-' + feed_source.item_date_field
        items = items.order_by(order_by).limit(int(feed_source.limit))

        for item in items:
            item_author = item[feed_source.item_author_field] or blog_author
            feed.add(
                get_item_title(item, feed_source.item_title_field),
                get_item_body(item, feed_source.item_body_field),
                xml_base=url_to(item, external=True),
                url=url_to(item, external=True),
                content_type='html',
                id=get_id(u'%s/%s' % (
                    ctx.env.project.id,
                    item['_path'].encode('utf-8'))),
                author=item_author,
                updated=get_item_updated(item, feed_source.item_date_field))

        with artifact.open('wb') as f:
            f.write(feed.to_string().encode('utf-8'))


class AtomPlugin(Plugin):
    name = u'Atom feed for Lektor'

    defaults = {
        'source_path': '/blog',
        'url_path': None,
        'filename': 'feed.xml',
        'blog_summary_field': 'summary',
        'items': None,
        'limit': 50,
        'item_title_field': 'title',
        'item_body_field': 'body',
        'item_author_field': 'author',
        'item_date_field': 'pub_date',
        'item_model': None,
    }

    def get_atom_config(self, feed, key):
        default_value = self.defaults[key]
        return self.get_config().get('%s.%s' % (feed, key), default_value)

    def on_setup_env(self, **extra):
        self.env.add_build_program(AtomFeedSource, AtomFeedBuilderProgram)

        def generate_feed(name, source):
            if source.path == self.get_atom_config(name, 'source_path'):
                yield AtomFeedSource(source, name, self)

        for feed_name in self.get_config().sections():
            self.env.generator(partial(generate_feed, feed_name))
