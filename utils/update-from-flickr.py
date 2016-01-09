from __future__ import print_function

import argparse
import json
import os
import shutil
import sys

import flickrapi  # from http://pypi.python.org/pypi/flickrapi
import requests
from lektor.utils import slugify

api_key = '24b43252c30181f08bd549edbb3ed394'
api_secret = '2f58307171bc644e'

parser = argparse.ArgumentParser(
    description='Update emptysquare slideshow from your Flickr account')
parser.add_argument(
    dest='flickr_username', action='store',
    help='Your Flickr username')


this_dir = os.path.dirname(sys.argv[0])
photo_dir = os.path.normpath(os.path.join(
    this_dir, '..', 'emptysquare', 'content', 'photography'))


def parse_flickr_json(json_string):
    """
    @param json_string: Like jsonFlickrApi({'key':'value', ...})
    @return: A native Python object, like dictionary or list
    """
    prefix = 'jsonFlickrApi('
    if json_string.startswith(prefix):
        json_string = json_string[len(prefix):]

        # Also ends with ')'
        json_string = json_string[:-1]

    return json.loads(json_string)


class JSONFlickr(object):
    def __init__(self, api_key, api_secret):
        """
        @param api_key: A Flickr API key
        """
        self.flickr = flickrapi.FlickrAPI(api_key, api_secret)

    def authenticate(self):
        self.flickr.authenticate_via_browser(perms='read')

    def __getattr__(self, attr):
        def f(**kwargs):
            kwargs_copy = kwargs.copy()
            kwargs_copy['format'] = 'json'
            return parse_flickr_json(
                getattr(self.flickr, attr)(**kwargs_copy)
            )

        return f


def first(it):
    try:
        for i in it:
            return i
    except StopIteration:
        return None


def get_photoset(uname, slug, target_dir, json_flickr, sets):
    try:
        fset, = (s for s in sets if slugify(s['title']['_content']) == slug)
    except ValueError:
        raise Exception("Couldn't find Flickr set for %r" % repr(slug))

    set_name = fset['title']['_content']
    print('Extracting photoset %s' % repr(set_name))
    photos = json_flickr.photosets_getPhotos(photoset_id=fset['id'])['photoset']

    for i, photo in enumerate(photos['photo']):
        flickr_url = 'http://www.flickr.com/photos/%s/%s' % (uname, photo['id'])

        response = json_flickr.photos_getSizes(photo_id=photo['id'])
        sizes = response['sizes']['size']

        try:
            orig = first(size for size in sizes if size['label'] == 'Original')
        except IndexError:
            raise Exception(
                "Couldn't find 'Original' size for photo %s at %s" % (
                    repr(photo['title']),
                    flickr_url))

        with open(os.path.join(target_dir, '%0.3d.jpg' % i), 'wb') as f:
            r = requests.get(orig['source'], stream=True)
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)

        sys.stdout.write('.')
        sys.stdout.flush()

    sys.stdout.write('\n')

    with open(os.path.join(target_dir, 'contents.lr'), 'w') as f:
        f.write('''_model: gallery
---
title: {title}
'''.format(title=set_name))


def main():
    args = parser.parse_args()
    json_flickr = JSONFlickr(api_key, api_secret)

    print('Getting user id')
    user = json_flickr.people_findByUsername(username=args.flickr_username)
    user_id = user['user']['nsid']
    print(user_id)

    print('Authenticating')
    json_flickr.authenticate()

    print('Getting sets')
    lst = json_flickr.photosets_getList(user_id=user_id)
    sets = lst['photosets']['photoset']

    for gallery_dir in os.listdir(photo_dir):
        target_dir = os.path.join(photo_dir, gallery_dir)
        if os.path.isdir(target_dir):
            get_photoset(uname=args.flickr_username,
                         slug=gallery_dir,
                         target_dir=target_dir,
                         json_flickr=json_flickr,
                         sets=sets)

if __name__ == '__main__':
    main()
