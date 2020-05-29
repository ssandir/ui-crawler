"""
Inspired by Craig Addyman (http://www.craigaddyman.com/parse-an-xml-sitemap-with-python/)
Enhanced by Viktor Petersson (http://viktorpetersson.com) / @vpetersson
Enhanced by Jari Turkia (https://blog.hqcodeshop.fi/) / @HQJaTu
Pulled from Git (https://gist.github.com/HQJaTu/cd66cf659b8ee633685b43c5e7e92f05)
Changed by vkriznar
"""

from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse
import logging


def get_sitemap_from(url):
    get_url = requests.get(url)

    if get_url.status_code == 200:
        return get_url.text
    else:
        logging.debug('Unable to fetch sitemap: %s.' % url)


def process_sitemap(s):
    soup = BeautifulSoup(s, 'lxml')
    result = []

    for loc in soup.findAll('loc'):
        result.append(loc.text)

    return result


def is_sitemap(url):
    parts = urlparse(url)
    return 'sitemap.xml' in parts.path


def parse_sitemap(s):
    sitemap = process_sitemap(s)
    result = []

    while sitemap:
        candidate = sitemap.pop()
        logging.debug('Parsing sitemap url: ' + candidate)

        if is_sitemap(candidate):
            sub_sitemap = get_sitemap_from(candidate)
            for i in process_sitemap(sub_sitemap):
                sitemap.append(i)
        else:
            result.append(candidate)

    return result


def get_sitemap(url):
    if is_sitemap(url):
        sitemap = get_sitemap_from(url)
        return parse_sitemap(sitemap)
    else:
        logging.debug('Not a valida sitemap url: %s' % url)
        return None
