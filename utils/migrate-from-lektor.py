from os import makedirs
from os.path import basename, join, exists

import click
from lektor.cli import pass_context
from shutil import copy2


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
        attachments = list(post.attachments)

        if post['thumbnail']:
            thumbnail = '\nthumbnail = "%s"' % post['thumbnail']
        elif attachments:
            thumbnail = '\nthumbnail = "%s"' % basename(
                attachments[0].attachment_filename)
        else:
            thumbnail = ''

        pub_date = post['pub_date'] if 'pub_date' in post else None
        is_draft = not pub_date or not post['_discoverable']

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
            'thumbnail': thumbnail,
            'draft_bool': 'true' if is_draft else 'false',
            'body': post['body'].__html__()
        }

        with open(path + '.md', 'w') as f:
            f.write((u"""+++
type = "{type}"
title = "{title}"
date = "{pub_date}"
description = "{summary}"
"blog/category" = [{categories_list}]
"blog/tag" = [{tags_list}]
enable_lightbox = {enable_lightbox_bool}{thumbnail}
draft = {draft_bool}
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
