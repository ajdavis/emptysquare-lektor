from __future__ import print_function

import os
import subprocess

import click
import sys


@click.command()
@click.argument('source', type=click.Path())
@click.argument('target', type=click.Path())
def photo_import(source, target):
    """Import photos into an article."""

    contents_path = os.path.join(target, 'contents.lr')

    if os.path.exists(contents_path):
        print('%s already exists' % contents_path, file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(target):
        os.makedirs(target)

    filenames = []

    for filename in os.listdir(source):
        ext = os.path.splitext(filename)[-1]
        if ext.lower() not in ('.png', '.jpg', '.jpeg'):
            continue

        print(filename)
        filenames.append(filename)

        source_path = os.path.join(source, filename)
        target_path = os.path.join(target, filename)
        subprocess.check_call(['convert', source_path, '-resize', '1200',
                               '-quality', '80', target_path])

    images_markdown = '\n\n***\n\n'.join("![](%s)" % fn for fn in filenames)

    with open(contents_path, 'w+') as f:
        f.write(u"""_model: blog-post
---
title:
---
pub_date:
---
_discoverable: no
---
type: post
---
tags:

---
categories:
---
summary:
---
body:

{images}
""".format(images=images_markdown).encode())


if __name__ == '__main__':
    photo_import()
