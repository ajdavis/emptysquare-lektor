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

for post in db.posts.find({'pub_date': {'$exists': True}}):
    slug = post['slug']
    post_dir = os.path.join(blog_dir, slug)
    shutil.rmtree(post_dir, ignore_errors=True)
    os.mkdir(post_dir)
    post_path = os.path.join(post_dir, 'contents.lr')
    post['tags'] = '\n'.join(post.get('tags', []))
    post['categories'] = '\n'.join(
        c['name'] for c in post.get('categories', []))
    post['summary'] = post.get('meta_description', post['summary'])
    post['original'] = urls.sub('/', post['original'])

    with open(post_path, 'w') as contents:
        print(post['title'])
        contents.write(u'''_model: blog-post
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

{original}'''.format(**post).encode(errors='ignore'))
