import os
import re
import shutil
import sys

import pymongo

db = pymongo.MongoClient().motorblog
this_dir = os.path.dirname(sys.argv[0])
blog_dir = os.path.normpath(os.path.join(
    this_dir, '..', 'emptysquare', 'content', 'blog'))

urls = re.compile(r'https?://(emptysquare.net|emptysqua.re)/')


def render_post(p, f):
    p['tags'] = '\n'.join(p.get('tags', []))
    p['categories'] = '\n'.join(
        c['name'] for c in p.get('categories', []))
    p['summary'] = p.get('meta_description', p['summary'])
    p['original'] = urls.sub('/', p['original'])

    print(p['title'])
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


def render_redirect(p, f):
    f.write(u'''_model: redirect
---
target: /blog/{redirect}
'''.format(**p).encode(errors='ignore'))


for post in db.posts.find({'pub_date': {'$exists': True}}):
    slug = post['slug']
    post_dir = os.path.join(blog_dir, slug)
    shutil.rmtree(post_dir, ignore_errors=True)
    os.mkdir(post_dir)
    post_path = os.path.join(post_dir, 'contents.lr')

    with open(post_path, 'w') as contents:
        if post['type'] in ('page', 'post'):
            render_post(post, contents)
        else:
            assert post['type'] == 'redirect'
            render_redirect(post, contents)
