#!/usr/bin/env python

"""Adapted from the Tornado spider example."""
import csv
import time
from datetime import timedelta

import sys

from tornado.httpclient import HTTPError

try:
    from HTMLParser import HTMLParser
    from urlparse import urljoin, urldefrag
except ImportError:
    from html.parser import HTMLParser
    from urllib.parse import urljoin, urldefrag

from tornado import httpclient, gen, ioloop, queues

base_url = sys.argv[1]
concurrency = 5
all_urls = {}


@gen.coroutine
def get_links_from_url(url):
    """Download the page at `url` and parse it for links.

    Returned links have had the fragment after `#` removed, and have been made
    absolute so, e.g. the URL 'gen.html#tornado.gen.coroutine' becomes
    'http://www.tornadoweb.org/en/stable/gen.html'.
    """
    try:
        response = yield httpclient.AsyncHTTPClient().fetch(
            url, follow_redirects=False)
        print('fetched %s' % url)
        all_urls[url] = True

        html = response.body if isinstance(response.body, str) \
            else response.body.decode()
        urls = [urljoin(url, remove_fragment(new_url))
                for new_url in get_links(html)]
    except Exception as e:
        if isinstance(e, HTTPError) and getattr(e, 'response', None) is not None:
            response = e.response
            if 300 <= response.code < 400 and 'Location' in response.headers:
                # Redirect.
                location = e.response.headers['Location']
                destination = urljoin(url, remove_fragment(location))
                all_urls[url] = destination
                urls = [destination]
                raise gen.Return(urls)

        print('Exception: %s %s' % (e, url))
        all_urls[url] = str(Exception)
        raise gen.Return([])

    raise gen.Return(urls)


def remove_fragment(url):
    pure_url, frag = urldefrag(url)
    return pure_url


def get_links(html):
    class URLSeeker(HTMLParser):
        def __init__(self):
            HTMLParser.__init__(self)
            self.urls = []

        def handle_starttag(self, tag, attrs):
            href = dict(attrs).get('href')
            if href and tag == 'a':
                self.urls.append(href)

    url_seeker = URLSeeker()
    url_seeker.feed(html)
    return url_seeker.urls


@gen.coroutine
def main():
    q = queues.Queue()
    start = time.time()
    fetching, fetched = set(), set()

    @gen.coroutine
    def fetch_url():
        current_url = yield q.get()
        try:
            if current_url in fetching:
                return

            print('fetching %s' % current_url)
            fetching.add(current_url)
            urls = yield get_links_from_url(current_url)
            fetched.add(current_url)

            for new_url in urls:
                # Only follow links beneath the base URL
                if new_url.startswith(base_url):
                    yield q.put(new_url)

        finally:
            q.task_done()

    @gen.coroutine
    def worker():
        while True:
            yield fetch_url()

    q.put(base_url)

    # Start workers, then wait for the work queue to be empty.
    for _ in range(concurrency):
        worker()
    yield q.join(timeout=timedelta(seconds=300))
    assert fetching == fetched

    with open('urls.csv', 'w') as f:
        csvfile = csv.DictWriter(f, ['url', 'response'])
        csvfile.writeheader()
        for url, response in sorted(all_urls.items()):
            csvfile.writerow({
                'url': url,
                'response': str(response)})

if __name__ == '__main__':
    import logging
    logging.basicConfig()
    io_loop = ioloop.IOLoop.current()
    io_loop.run_sync(main)
