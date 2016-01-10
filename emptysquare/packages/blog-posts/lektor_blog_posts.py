# -*- coding: utf-8 -*-
from lektor.context import get_ctx
from lektor.db import F
from lektor.pluginsystem import Plugin
from lektor.types import Type
import markdown  # This is "Python Markdown": pip install markdown


def blog_posts():
    ctx = get_ctx()
    return ctx.record.pagination.items.filter(F._model == 'blog-post' and
                                              F.type == 'post')


class HTML(object):
    def __init__(self, html):
        self.html = html

    def __html__(self):
        return self.html


class MotorBlogMarkdownType(Type):
    def value_from_raw(self, raw):
        return HTML(markdown.markdown(raw.value or u'', extensions=[
            'codehilite(linenums=False,noclasses=True)',
            'fenced_code',
            'extra',
            'toc']))


class BlogPostsPlugin(Plugin):
    name = u'blog-posts'
    description = u'Lektor customization just for emptysqua.re.'

    def on_setup_env(self, **extra):
        self.env.types['motor_blog_markdown'] = MotorBlogMarkdownType
        self.env.jinja_env.globals['blog_posts'] = blog_posts

    def get_blog_path(self):
        return self.get_config().get('blog_path', '/blog')
