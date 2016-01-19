# -*- coding: utf-8 -*-

import datetime
import os
import pkg_resources
import re
import subprocess

import click
from lektor.cli import pass_context
from lektor.db import F
from lektor.pluginsystem import Plugin
from lektor.types import Type
import markdown  # This is "Python Markdown": pip install markdown


version = pkg_resources.get_distribution('lektor-blog-posts').version


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

    def get_blog_path(self):
        return self.get_config().get('blog_path', '/blog')


@click.group()
@click.option('--project', type=click.Path(),
              help='The path to the lektor project to work with.')
@click.version_option(prog_name='Lektor', version=version)
@pass_context
def cli(ctx, project=None):
    """emptysqua.re blog utility."""
    if project is not None:
        ctx.set_project_path(project)

    ctx.load_plugins()


@cli.command('list')
@click.argument('what', type=click.Choice(['drafts', 'tags']))
@pass_context
def list_what(ctx, what):
    pad = ctx.get_env().new_pad()

    if what == 'drafts':
        q = pad.query('blog').include_undiscoverable(True)
        for draft in q.filter(F._model == 'blog-post'):
            pub_date = draft['pub_date'] if 'pub_date' in draft else None

            if not pub_date or not draft['_discoverable']:
                print '%s%s' % (str(draft.path.ljust(40)),
                                ' "%s"' % draft['title'] if draft['title']
                                else '')

                if draft['_discoverable']:
                    print 'Warning: discoverable'

                if draft['pub_date']:
                    print 'Warning: pub_date'

    elif what == 'tags':
        for tag in sorted(pad.query('blog').distinct('tags')):
            print tag
    else:
        raise NotImplementedError(what)


@cli.command('new')
@click.argument('what', type=click.Choice(['draft']))
@click.argument('where', type=click.Path())
@pass_context
def new(ctx, what, where):
    if what == 'draft':
        project_dir = os.path.dirname(ctx.get_project().project_path)
        path = os.path.join(project_dir, 'content', where)
        if os.path.exists(path):
            click.BadParameter("%s already exists!" % path)

        os.makedirs(path)
        contents_path = os.path.join(path, 'contents.lr')
        with open(contents_path, 'w+') as f:
            f.write("""_model: blog-post
---
title:
---
type: post
---
tags:

---
categories:
---
_discoverable: no
---
pub_date:
---
summary:
---
body:


""")
        print contents_path
        subprocess.call(['open', contents_path])
    else:
        raise NotImplementedError(what)


@cli.command('publish')
@click.argument('where', type=click.Path())
@pass_context
def new(ctx, where):
    pad = ctx.get_env().new_pad()
    post = pad.get('blog/' + where)
    if not post:
        click.BadParameter('"%s" does not exist!' % where)

    if post['pub_date'] and post['_discoverable']:
        click.BadParameter('"%s" already published!' % where)

    contents = post.contents.as_text()
    if not post['pub_date']:
        contents = """pub_date: %s
---
%s""" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), contents)

    if not post['_discoverable']:
        pat = re.compile(r'^_discoverable:\s*(no|false)$', re.MULTILINE)
        assert 1 == len(pat.findall(contents))
        contents = pat.sub('_discoverable = yes', contents)

    with open(post.source_filename, 'w') as f:
        f.write(contents)
