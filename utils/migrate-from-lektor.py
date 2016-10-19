from os import makedirs
from os.path import basename, join, exists, splitext
from shutil import copy2

import click
from jinja2 import Undefined
from lektor.cli import pass_context
from lektor.imagetools import get_image_info, computed_height, get_quality
from lektor.utils import portable_popen


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


@click.command()
@click.argument('destination', type=click.Path())
@pass_context
def cli(ctx, destination):
    ctx.load_plugins()
    pad = ctx.get_env().new_pad()

    print('listing posts...')

    for post in pad.query('/blog'):
        print(post.path)
        path = join(destination, basename(post.path))
        thumbnail_attachment = featured_img(post)
        if thumbnail_attachment:
            source_img = thumbnail_attachment.attachment_filename
            root, ext = splitext(source_img)
            thumbnail_filename = '%s@240%s' % (basename(root), ext)
            target_img = join(path, thumbnail_filename)
            if not exists(target_img):
                with open(source_img, 'rb') as f:
                    _, w, h = get_image_info(f)

                if w <= 240:
                    # Don't resize.
                    copy2(source_img, target_img)
                else:
                    # Can't use process_image without a build context.
                    height = computed_height(source_img, 240, w, h)
                    cmdline = ['convert', source_img,
                               '-resize', '240x%d' % height,
                               '-auto-orient',
                               '-quality', str(get_quality(source_img)),
                               target_img]

                    portable_popen(cmdline).wait()

            thumbnail_front_matter = '\nthumbnail = "%s"' % thumbnail_filename
        else:
            thumbnail_front_matter = ''

        pub_date = post['pub_date'] if 'pub_date' in post else None
        is_draft = not pub_date or not post['_discoverable']
        legacy_id_front_matter = ('\nlegacyid = "%s"' % post['legacy_id']
                                  if 'legacy_id' in post else '')
        props = {
            'type': post['type'],
            'title': post['title'].replace('"', r'\"'),
            'pub_date': post['pub_date'].isoformat(),
            'summary': post['summary'].replace('"', r'\"'),
            'categories_list': ', '.join(
                '"%s"' % c for c in post['categories']),
            'tags_list': ', '.join(
                '"%s"' % t for t in post['tags']),
            'enable_lightbox_bool': (
                'true' if post['enable_lightbox']
                else 'false'),
            'thumbnail': thumbnail_front_matter,
            'draft_bool': 'true' if is_draft else 'false',
            'legacy': legacy_id_front_matter,
            'body': post['body'].__html__()
        }

        with open(path + '.md', 'w') as f:
            f.write((u"""+++
type = "{type}"
title = "{title}"
date = "{pub_date}"
description = "{summary}"
category = [{categories_list}]
tag = [{tags_list}]
enable_lightbox = {enable_lightbox_bool}{thumbnail}
draft = {draft_bool}{legacy}
+++

{body}
    """.format(**props)).encode('utf-8'))

        attachments = list(post.attachments)
        if attachments:
            if not exists(path):
                makedirs(path)

            for a in attachments:
                print("\t%s" % basename(a.attachment_filename))
                copy2(a.attachment_filename,
                      join(path, basename(a.attachment_filename)))

cli()
