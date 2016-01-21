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
@click.option('-1', '--one', is_flag=True, default=False)
@click.argument('what',
                type=click.Choice(['posts', 'drafts', 'tags']),
                default='posts')
@pass_context
def blog_list(ctx, one, what):
    pad = ctx.get_env().new_pad()

    if what == 'tags':
        for tag in sorted(pad.query('blog').distinct('tags')):
            print tag

    else:
        q = pad.query('blog').include_undiscoverable(True)
        q = q.filter(F._model == 'blog-post')

        for post in q:
            pub_date = post['pub_date'] if 'pub_date' in post else None

            is_draft = not pub_date or not post['_discoverable']
            draft_str = ' (draft)' if is_draft else ''

            path = post.path
            if path.startswith('/blog/'):
                path = path[len('/blog/'):]

            title = ' "%s"' % post['title'] if post['title'] else ''
            if what == 'drafts' and not is_draft:
                continue

            if one:
                print path
            else:
                print u''.join((str(path.ljust(40)), title, draft_str))

                if is_draft and post['_discoverable']:
                    print '\tWARNING: DISCOVERABLE!'

                if is_draft and post['pub_date']:
                    print '\tWARNING: PUB_DATE!'


@cli.command('new')
@click.argument('what', type=click.Choice(['draft']))
@click.argument('where', type=click.Path())
@click.argument('images', type=click.Path(), required=False)
@pass_context
def blog_new(ctx, what, where, images):
    if what == 'draft':
        project_dir = ctx.get_project().tree
        path = os.path.join(project_dir, 'content', 'blog', where)
        if os.path.exists(path):
            raise click.BadParameter("%s already exists!" % path)

        os.makedirs(path)
        contents_path = os.path.join(path, 'contents.lr')

        if images:
            if os.path.isdir(images):
                filenames = os.listdir(images)
            elif os.path.isfile(images):
                filenames = [images]
            else:
                raise click.BadParameter('"%s" does not exist!' % images)

            for filename in filenames:
                ext = os.path.splitext(filename)[-1]
                if ext.lower() not in ('.png', '.jpg', '.jpeg'):
                    continue

                print(filename)
                filenames.append(filename)

                source_path = os.path.join(images, filename)
                target_path = os.path.join(path, filename)
                subprocess.check_call(
                    ['convert', source_path, '-resize', '1200',
                     '-quality', '80', target_path])

            images_markdown = '\n\n***\n\n'.join(
                "![](%s)" % fn for fn in filenames)

        else:
            images_markdown = ''

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

%s
""" % images_markdown)
        print contents_path
        subprocess.call(['open', contents_path])
    else:
        raise NotImplementedError(what)


@cli.command('publish')
@click.argument('where', type=click.Path())
@pass_context
def blog_publish(ctx, where):
    pad = ctx.get_env().new_pad()
    post = pad.get('blog/' + where)
    if not post:
        raise click.BadParameter('"%s" does not exist!' % where)

    if post['pub_date'] and post['_discoverable']:
        raise click.BadParameter('"%s" already published!' % where)

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


@cli.command('open')
@click.option('--charm', is_flag=True)
@click.argument('where', type=click.Path())
@pass_context
def blog_open(ctx, charm, where):
    pad = ctx.get_env().new_pad()
    post = pad.get('blog/' + where)
    if not post:
        raise click.BadParameter('"%s" does not exist!' % where)

    program = 'charm' if charm else 'open'
    subprocess.call([program, post.source_filename])


@cli.command('preview')
@click.argument('where', type=click.Path())
@pass_context
def blog_preview(ctx, where):
    import webbrowser

    pad = ctx.get_env().new_pad()
    post = pad.get('blog/' + where)
    if not post:
        raise click.BadParameter('"%s" does not exist!' % where)

    webbrowser.open("http://localhost:5000" + post.url_path)
