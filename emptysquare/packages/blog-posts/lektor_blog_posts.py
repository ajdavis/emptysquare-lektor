# -*- coding: utf-8 -*-

import datetime
import os
import shutil
import webbrowser
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

try:
    from pync import Notifier
except (ImportError, OSError):
    Notifier = None

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


def featured_img(blog_post):
    if not blog_post or not blog_post.attachments.images:
        return

    if not isinstance(blog_post['thumbnail'], Undefined):
        fn = blog_post['thumbnail']
        for img in blog_post.attachments.images:
            if img.attachment_filename.split('/')[-1] == fn:
                return img
        else:
            raise RuntimeError("Post '%s' names absent thumbnail '%s'" % (
                blog_post['_id'], fn))
    else:
        return blog_post.attachments.images.all()[0]


def post_thumbnail(blog_post):
    feat = featured_img(blog_post)
    if feat:
        return feat.thumbnail(120)


class BlogPostsPlugin(Plugin):
    name = u'blog-posts'
    description = u'Lektor customization just for emptysqua.re.'

    def on_setup_env(self, **extra):
        self.env.types['motor_blog_markdown'] = MotorBlogMarkdownType
        self.env.jinja_env.filters['featured_img'] = featured_img
        self.env.jinja_env.filters['post_thumbnail'] = post_thumbnail

    def on_after_build_all(self, builder, **extra):
        if Notifier:
            Notifier.notify("Build complete", title="Lektor")

    def get_blog_path(self):
        return self.get_config().get('blog_path', '/blog')


def write(path, contents):
    with open(path, 'w') as f:
        f.write(contents.encode('utf-8'))


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
                type=click.Choice(['posts', 'pages', 'drafts', 'tags', 'categories']),
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
        if what == 'posts':
            q = q.filter(F.type == 'post')
        elif what == 'pages':
            q = q.filter(F.type == 'page')

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
            images = os.path.normpath(os.path.expanduser(images))
            if os.path.isdir(images):
                filenames = os.listdir(images)
            elif os.path.isfile(images):
                filenames = [images]
            else:
                raise click.BadParameter('"%s" does not exist!' % images)

            image_filenames = []
            for filename in filenames:
                ext = os.path.splitext(filename)[-1]
                if ext.lower() not in ('.png', '.jpg', '.jpeg'):
                    continue

                print(filename)

                image_filenames.append(filename)
                source_path = os.path.join(images, filename)
                target_path = os.path.join(path, filename)
                shutil.copy(source_path, target_path)

            images_markdown = '\n\n***\n\n'.join(
                "![](%s)" % fn for fn in image_filenames)

            images_markdown += """
***
<span style="color: gray">Images &copy; A. Jesse Jiryu Davis</span>"""

            lightbox = """enable_lightbox: true
---
"""

        else:
            images_markdown = ''
            lightbox = ''

        write(contents_path, """_model: blog-post
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
%sbody:

%s
""" % (lightbox, images_markdown))

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

    if not post['categories'] and post['type'] == 'post':
        raise click.BadParameter('"%s" no categories!' % where)

    # Require author to choose one image as the thumbnail.
    if post.attachments.images.count() > 1:
        if not post['thumbnail']:
            raise click.BadParameter('"%s" no thumbnail!' % where)
        else:
            thumb_file = os.path.join(
                os.path.dirname(post.source_filename),
                post['thumbnail'])
            if not os.path.isfile(thumb_file):
                raise click.BadParameter('thumbnail "%s" not found!'
                                         % post['thumbnail'])

    extra_categories = (set(post['categories']) -
                        pad.query('category').distinct('name'))
    if extra_categories:
        raise click.BadParameter('"%s" bad categories: %s' %
                                 (where, ', '.join(extra_categories)))

    contents = post.contents.as_text()
    if not post['pub_date']:
        pub_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if 'pub_date' in contents:
            # There is a pub_date line, it's just not a valid datetime.
            pat = re.compile(r'^pub_date:.*?$', re.MULTILINE)
            assert 1 == len(pat.findall(contents)), "Couldn't set pub_date"
            contents = pat.sub('pub_date: ' + pub_date, contents)
        else:
            # No pub_date line at all.
            contents = """pub_date: %s
---
%s""" % (pub_date, contents)

    if not post['_discoverable']:
        pat = re.compile(r'^_discoverable:\s*(no|false)$', re.MULTILINE)
        assert 1 == len(pat.findall(contents))
        contents = pat.sub('_discoverable: yes', contents)

    write(post.source_filename, contents)
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


@cli.command('reveal')
@click.argument('where', type=click.Path())
@pass_context
def blog_reveal(ctx, where):
    subprocess.call(['open', os.path.join('content/blog', where)])


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


@cli.command('visit')
@click.argument('where', type=click.Path())
@pass_context
def blog_visit(ctx, where):
    pad = ctx.get_env().new_pad()
    post = pad.get('blog/' + where)
    if not post:
        raise click.BadParameter('"%s" does not exist!' % where)

    webbrowser.open(pad.make_url(post.url_path, external=True))


@cli.command('path')
@click.argument('where', type=click.Path())
@pass_context
def blog_path(ctx, where):
    print os.path.join('content/blog', where)
