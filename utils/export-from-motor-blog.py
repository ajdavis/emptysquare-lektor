import os
import re
import shutil
import sys
import urllib
from functools import partial

import gridfs
import pymongo

db = pymongo.MongoClient().motorblog
gfs = gridfs.GridFS(db)

this_dir = os.path.dirname(sys.argv[0])
blog_dir = os.path.normpath(os.path.join(
    this_dir, '..', 'emptysquare', 'content', 'blog'))

urls = re.compile(
    r'https?://(emptysquare.net|emptysqua.re)/')

imgs = re.compile(r'<img(?P<pre>\s.*?)src="/blog/media/'
                  r'(?P<path>(.*?)(/|%2F)(?P<name>[^"/]+))"'
                  r'(?P<post>.*?)/?>')


def replace_img(post_dir, match):
    path = match.group('path')
    name = match.group('name')

    # I once quoted a few paths by accident with Motor-Blog.
    gridout = gfs.get_last_version(urllib.unquote(path))
    with open(os.path.join(post_dir, name), 'wb') as f:
        f.write(gridout.read())

    return match.expand(r'<img\g<pre>src="\g<name>"\g<post>/>')


def render_post(p, post_dir, f):
    print(p['title'])

    p['tags'] = '\n'.join(p.get('tags', []))
    p['categories'] = '\n'.join(
        c['name'] for c in p.get('categories', []))
    p['summary'] = p.get('meta_description', p['summary'])
    p['original'] = urls.sub('/', p['original'])
    p['original'] = imgs.sub(partial(replace_img, post_dir), p['original'])

    f.write(u'''_model: blog-post
---
title: {title}
---
pub_date: {pub_date:%Y-%m-%d}
---
author: {author}
---
type: {type}
---
tags:

{tags}
---
categories:

{categories}
---
summary: {summary}
---
body:

{original}
'''.format(**p).encode(errors='ignore'))


def render_redirect(p, _, f):
    f.write(u'''_model: redirect
---
target: /blog/{redirect}
'''.format(**p).encode(errors='ignore'))


def main():
    for p in db.posts.find({'status': 'publish'}):
        slug = p['slug']
        post_dir = os.path.join(blog_dir, slug)
        shutil.rmtree(post_dir, ignore_errors=True)
        os.mkdir(post_dir)
        post_path = os.path.join(post_dir, 'contents.lr')

        with open(post_path, 'w') as contents:
            if p['type'] in ('page', 'post'):
                render_post(p, post_dir, contents)
            else:
                assert p['type'] == 'redirect'
                render_redirect(p, post_dir, contents)

if __name__ == '__main__':
    main()
