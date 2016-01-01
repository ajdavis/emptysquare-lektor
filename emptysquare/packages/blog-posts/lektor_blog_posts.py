# -*- coding: utf-8 -*-
from lektor.context import get_ctx
from lektor.db import F
from lektor.pluginsystem import Plugin


def blog_posts():
    pad = get_ctx().pad
    return pad.get('blog').pagination.items.filter(F._model == 'blog-post')


class BlogPostsPlugin(Plugin):
    name = u'blog-posts'
    description = u'Just for emptysqua.re: filter pagination of blog posts.'

    def on_setup_env(self, **extra):
        self.env.jinja_env.globals.update(blog_posts=blog_posts)
