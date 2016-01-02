# -*- coding: utf-8 -*-
from lektor.context import get_ctx
from lektor.db import F
from lektor.pluginsystem import Plugin


def blog_posts():
    ctx = get_ctx()
    return ctx.record.pagination.items.filter(F._model == 'blog-post' and F.type == 'post')


def pub_date(dt):
    return '%s %s, %s' % (dt.strftime('%b'), dt.day, dt.year)


class BlogPostsPlugin(Plugin):
    name = u'blog-posts'
    description = u'Just for emptysqua.re: filter pagination of blog posts.'

    def on_setup_env(self, **extra):
        jinja_env = self.env.jinja_env
        jinja_env.globals['blog_posts'] = blog_posts
        jinja_env.filters['pub_date'] = pub_date
