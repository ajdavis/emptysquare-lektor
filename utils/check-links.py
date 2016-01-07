import os
import re
import sys


import csv


page_pattern = re.compile(r'https?://emptysqua\.re/blog/.*?/page/\d+/$')


https = 'https://emptysqua.re/'
http = 'http://emptysqua.re/'

directory = os.path.expanduser(sys.argv[2])
assert os.path.isdir(directory)

for row in csv.DictReader(open(sys.argv[1])):
    if not row['Status'].startswith('200'):
        continue

    url = row['URL']
    if url.startswith(https):
        path = url[len(https):]
    elif url.startswith(http):
        path = url[len(http):]
    else:
        print url
        continue

    if page_pattern.match(url):
        continue

    target = os.path.join(directory, path)
    if not os.path.isdir(target):
        print target

    if path.endswith('/'):
        index = os.path.join(target, 'index.html')
        if not os.path.isfile(index):
            print index
