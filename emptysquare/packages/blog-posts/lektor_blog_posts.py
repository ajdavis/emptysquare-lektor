# -*- coding: utf-8 -*-

import datetime
import os
from collections import defaultdict, OrderedDict

import pkg_resources
import re
import subprocess

import click
from jinja2 import Undefined
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


def post_thumbnail(blog_post):
    if not blog_post or not blog_post.attachments.images:
        return

    if not isinstance(blog_post['thumbnail'], Undefined):
        fn = blog_post['thumbnail']
        for img in blog_post.attachments.images:
            if img.attachment_filename.split('/')[-1] == fn:
                thumb = img
                break
        else:
            raise RuntimeError("Post '%s' names absent thumbnail '%s'" % (
                blog_post['_id'], fn))
    else:
        thumb = blog_post.attachments.images.all()[0]

    return thumb.thumbnail(120)


class BlogPostsPlugin(Plugin):
    name = u'blog-posts'
    description = u'Lektor customization just for emptysqua.re.'

    def on_setup_env(self, **extra):
        self.env.types['motor_blog_markdown'] = MotorBlogMarkdownType
        self.env.jinja_env.filters['post_thumbnail'] = post_thumbnail

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
                type=click.Choice(['posts', 'drafts', 'tags', 'categories']),
                default='posts')
@pass_context
def blog_list(ctx, one, what):
    pad = ctx.get_env().new_pad()

    if what == 'tags':
        for tag in sorted(pad.query('blog').distinct('tags')):
            print tag

    elif what == 'categories':
        for cat in sorted(pad.query('category').distinct('name')):
            print cat

    else:
        q = pad.query('blog').include_undiscoverable(True)
        q = q.filter(F._model == 'blog-post')

        for post in q:
            pub_date = post['pub_date'] if 'pub_date' in post else None

            is_draft = not pub_date or not post['_discoverable']
            draft_str = ' (draft)' if is_draft and what != 'drafts' else ''

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


class NetlifyHeaders(object):
    def __init__(self, pad):
        self.path = os.path.join(pad.asset_root.source_filename, '_headers')
        self.url_map = defaultdict(OrderedDict)
        self.open()

    def open(self):
        if not os.path.exists(self.path):
            return

        f = open(self.path)

        # Parse it. See https://www.netlify.com/docs/headers-and-basic-auth
        current_url_headers = None

        for line in f.readlines():
            if line.lstrip().startswith('#'):
                # Comment.
                continue
            elif line.lstrip() == line:
                # Does not start with whitespace: new URL pattern.
                url_pattern = line.rstrip()
                current_url_headers = self.url_map[url_pattern]
            else:
                # Starts with whitespace.
                if current_url_headers is not None:
                    if not line.strip():
                        continue
                    name, value = line.split(':', 1)
                    current_url_headers[name.strip()] = value.strip()

        f.close()

    def protect(self, record, username, password):
        headers = self.url_map[record.url_path]
        creds = headers['Basic-Auth'].split() if 'Basic-Auth' in headers else []
        cred = '%s:%s' % (username, password)
        if cred not in creds:
            creds.append(cred)
            self.url_map[record.url_path]['Basic-Auth'] = ' '.join(creds)

    def unprotect(self, record):
        self.url_map[record.url_path].pop('Basic-Auth', None)

    def save(self):
        with open(self.path, 'w') as f:
            for url_pattern, headers in self.url_map.items():
                # Article was unprotected or otherwise has no headers.
                if not headers:
                    continue

                f.write(url_pattern + '\n')
                f.write('\n'.join('  %s: %s' % (name, value)
                                  for name, value in headers.items()))

                f.write('\n')

            f.truncate()


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

    if not post['summary']:
        raise click.BadParameter('"%s" missing summary!' % where)

    summary_len = len(post['summary'])
    if summary_len > 150:
        raise click.BadParameter('"%s" summary is too long: %d' %
                                 (where, summary_len))

    if not post['title']:
        raise click.BadParameter('"%s" missing title!' % where)

    if not post['categories']:
        raise click.BadParameter('"%s" no categories!' % where)

    extra_categories = (set(post['categories']) -
                        pad.query('category').distinct('name'))
    if extra_categories:
        raise click.BadParameter('"%s" bad categories: %s' %
                                 (where, ', '.join(extra_categories)))

    contents = post.contents.as_text()
    if not post['pub_date']:
        contents = """pub_date: %s
---
%s""" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), contents)

    if not post['_discoverable']:
        pat = re.compile(r'^_discoverable:\s*(no|false)$', re.MULTILINE)
        assert 1 == len(pat.findall(contents))
        contents = pat.sub('_discoverable: yes', contents)

    with open(post.source_filename, 'w') as f:
        f.write(contents)

    headers = NetlifyHeaders(pad)
    headers.unprotect(post)
    headers.save()


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


@cli.command('protect')
@click.argument('where', type=click.Path())
@click.argument('username')
@click.argument('password')
@pass_context
def blog_protect(ctx, where, username, password):
    pad = ctx.get_env().new_pad()
    post = pad.get('blog/' + where)
    if not post:
        raise click.BadParameter('"%s" does not exist!' % where)

    if post['pub_date'] and post['_discoverable']:
        raise click.BadParameter('"%s" already published!' % where)

    headers = NetlifyHeaders(pad)
    headers.protect(post, username, password)
    headers.save()
