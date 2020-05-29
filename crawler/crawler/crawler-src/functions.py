import re
from urllib.parse import urlparse
import urllib.robotparser
import time
from datetime import datetime
from web_manager import *
from sitemap_parser import get_sitemap
import socket
import requests
import logging
from LinkCleaner import LinkCleaner


SLEEP_WAIT_SECONDS = 2
SLEEP_TH_SECONDS = 1
MIN_ROBOTS_CONTENT_LEN = 5


def request_delay_wait(coredb, server_id, delay):
    last_visit = coredb.lock_server(server_id)
    while last_visit is None:
        logging.debug("Waiting {} seconds for server {} to fetch robots.txt".format(SLEEP_WAIT_SECONDS, server_id))
        time.sleep(SLEEP_WAIT_SECONDS)
        last_visit = coredb.lock_server(server_id)

    diff_in_seconds = (datetime.utcnow() - last_visit[0]).total_seconds()
    if delay - diff_in_seconds > SLEEP_TH_SECONDS:
        logging.debug("Waiting {} seconds for server {} to fetch robots.txt".format(diff_in_seconds, server_id))
        time.sleep(diff_in_seconds)

    coredb.update_server_last_visit(server_id, datetime.utcnow())


def get_robots_txt(scheme, domain, bot_name, coredb, server_id):
    url = scheme + '://' + domain + '/robots.txt'
    try:
        r = requests.get(url, verify=False, headers={'User-Agent': bot_name})
        if r.status_code == 200:
            logging.debug('Found robots.txt at: ' + url)
            return r.text
        else:
            logging.debug('No robots.txt found at ' + url)
            return None
    except:
        logging.error('ERROR while searching for robots.txt at ' + url)
        return None


def get_ip_for_hostname(hostname):
    try:
        return socket.gethostbyname(hostname)
    except:
        return None


def extract_info_from_url(url):
    try:
        parsed = urlparse(url)
        server_ip = get_ip_for_hostname(parsed.netloc)
        return parsed.scheme, parsed.netloc, server_ip
    except Exception as e:
        logging.error(e)
        return None, None, None


def is_imdb_site(site):
    return bool(re.search('(^|\\.)imdb\\.com', site, re.IGNORECASE))


def is_robots_valid(content):
    if content is None:
        return False

    if '<html' in content or '<body' in content or len(content) < MIN_ROBOTS_CONTENT_LEN:
        return False
    return True


def create_new_site(scheme, site, server_id, bot_name, delay, coredb):
    request_delay_wait(coredb, server_id, delay)

    robots_content = get_robots_txt(scheme, site, bot_name, coredb, server_id)
    if not is_robots_valid(robots_content):
        robots_content = None

    site_map_urls = None
    if robots_content is not None:
        robots = urllib.robotparser.RobotFileParser()
        robots.parse(robots_content.splitlines())
        new_delay = robots.crawl_delay(bot_name)
        if new_delay is not None and new_delay > delay:
            delay = new_delay
        site_map_urls = robots.site_maps()

    return {'site': coredb.add_site(site, server_id, robots_content, site_map_urls, delay),
            'sitemap': site_map_urls}


def is_url_allowed(url, site_obj, bot_name):
    try:
        if site_obj['robots_content'] is None:
            return True
        robots = urllib.robotparser.RobotFileParser()
        robots.parse(site_obj['robots_content'].splitlines())
        return robots.can_fetch(bot_name, url)
    except:
        return False


def handle_sitemap(coredb, site_id, sitemap_urls, locks):
    sitemap_res = set()
    for s_url in sitemap_urls:
        logging.info('Getting sitemap for url: ' + s_url)
        s_map = get_sitemap(s_url)
        if s_map is not None:
            for s in s_map:
                s = LinkCleaner.clean(s)
                if s is not None:
                    sitemap_res.add(s)
    with locks['page']:
        logging.info('Sitemap returned: ' + repr(sitemap_res))
        for url in sitemap_res:
            logging.info('Adding sitemap page to db with url: ' + url)
            coredb.add_page(site_id, url)


def handle_new_page(coredb, url, crawler_config, locks, link_from_id=None):
    scheme, site, server_ip = extract_info_from_url(url)

    if site is None or server_ip is None:
        logging.debug('Skipping page {} due to extraction info problem'.format(url))
        return

    if is_imdb_site(site) is False:
        logging.debug('Skipping page {} due to gov.si filter'.format(url))
        return

    # Handle server
    with locks['server']:
        server_obj = coredb.get_server_by_ip_address(server_ip)
        if server_obj is None:
            server_obj = coredb.add_server(server_ip, datetime.fromtimestamp(0))

    # Handle site
    sitemap_urls = None
    with locks['site']:
        site_obj = coredb.get_site_by_domain(site)
        if site_obj is None:
            new_site_obj = create_new_site(scheme,
                                       site,
                                       server_obj['id'],
                                       crawler_config['bot_name'],
                                       crawler_config['request_delay'],
                                       coredb)
            site_obj = new_site_obj['site']
            #if new_site_obj['sitemap'] is not None:
                #sitemap_urls = new_site_obj['sitemap']

    # Handle sitemap outside of site lock
    if sitemap_urls is not None:
        handle_sitemap(coredb, site_obj['id'], sitemap_urls, locks)

    # Site has sitemap
    #if site_obj['sitemap_content'] is not None:
    #    logging.debug('Skipp adding page {}  - sitemap exists, added pages from sitemap.'.format(url))
    #    return

    # Is url allowed by robots
    if not is_url_allowed(url, site_obj, crawler_config['bot_name']):
        logging.debug('Skipping page {} due to robots.txt limit'.format(url))
        return

    # Handle page
    with locks['page']:
        page_obj = coredb.get_page_by_url(url)
        if page_obj is None and site_obj['sitemap_content'] is None:
            page_obj = coredb.add_page(site_obj['id'], url)

    # Link page
    if link_from_id is not None and page_obj is not None:
        coredb.add_link(link_from_id, page_obj['id'])
