from ConfigManager import ConfigManager
from functions import *

from hashlib import md5
import re
import time
from selenium.common.exceptions import TimeoutException
from CoreDb import PageType, DataType
from seleniumwire import webdriver
from urllib.parse import urlparse, urljoin
import logging
from LinkCleaner import LinkCleaner
from cleaner import Cleaner
PAGE_GET_SLEEP_SECONDS = 2


def init_selenium():
    cm = ConfigManager()
    crawler_config = cm.get_crawler_params()

    options = webdriver.ChromeOptions()
    options.headless = True  # We have no GUI
    options.add_argument('--disable-notifications')  # Pls no alerts (might be deprecated and not work at all)
    options.add_argument('--disable-dev-shm-usage')  # Some resource/storage stuff
    options.add_argument('--no-sandbox')  # Rip security, but doesn't work otherwise
    options.add_argument('user-agent=' + crawler_config['bot_name'])  # Course stuff
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(crawler_config['chromedriver_path'], options=options)
    driver.set_page_load_timeout(crawler_config['selenium_timeout'])
    return driver


def get_status_code_and_content_type(driver):
    # let us follow the redirects and find correct response
    if len(driver.requests) == 0:
        return None, None

    response = None
    for i in range(len(driver.requests)):
        if driver.requests[i].response is None:
            # Server did not answer this
            break

        status_code = driver.requests[i].response.status_code
        if status_code not in [301, 302, 303, 307, 308]:
            response = driver.requests[i].response
            break
    else:
        # redirects till end
        response = driver.requests[-1].response

    if response is None:
        # There were no response from server
        return None, None

    status_code = response.status_code  # like "200"
    try:
        content_type = response.headers['Content-Type']  # like "text/html; charset=UTF-8"
    except:
        return status_code, None

    # https://stackoverflow.com/questions/4212861/what-is-a-correct-mime-type-for-docx-pptx-etc
    mapping = {
        'text/html': 'html',
        'application/pdf': DataType.PDF,
        'application/msword': DataType.DOC,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DataType.DOCX,
        'application/vnd.ms-powerpoint': DataType.PPT,
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': DataType.PPTX
    }

    for key, value in mapping.items():
        if content_type.startswith(key):
            content_type = value
            break

    return status_code, content_type


def handle_new_link(coredb, config, url, from_id, locks):
    # don't want links to .js, .css, .ico files
    if re.match('\\.(js|css|ico)$', url) is not None:
        return

    if url is not None:
        handle_new_page(coredb, url, config, locks, from_id)


def handle_new_image(coredb, page_id, img_url):
    filename, file_type = extract_filename_and_file_type(img_url)

    # Validate filename
    if filename is None or len(filename) > 255 or '?' in filename:
        logging.error('Invalid image filename: {}'.format(filename))
        return

    # Validate file_type, it can be None
    if file_type is not None and len(file_type) > 50:
        logging.error('Invalid image file-type: {}'.format(file_type))
        return

    logging.debug("Adding new image with name {} and type {}".format(filename, file_type))
    coredb.add_img(page_id, filename, file_type)


def extract_filename_and_file_type(img_url):
    img_url = img_url.strip('/')
    filename = img_url[img_url.rfind('/')+1:]
    type = None
    splited = filename.split('.')
    if len(splited) > 1:
        type = splited[-1]
    return filename, type


def get_clean_source(source):
    return source.encode('utf-8', 'ignore').decode('utf-8')


def get_source_hash(source):
    return md5(source.encode('utf-8')).hexdigest()


def get_links_from_page(driver, source):
    # links
    links = driver.find_elements_by_xpath("//*[@href]")
    hrefs = list(map(lambda x: x.get_attribute('href'), links))
    # locations
    hrefs2 = re.findall('location(\\.href)?(\\s*)=(\\s*)"(.+?)"', source)

    all_links = hrefs + hrefs2
    cleaned_links = set()
    # Relative to absolute links
    for link in all_links:
        if bool(urlparse(link).netloc) is False:
            link = urljoin(driver.current_url, link)
        link = LinkCleaner.clean(link)
        if link is not None:
            cleaned_links.add(link)
    return cleaned_links


def process_html_page(coredb, driver, page, config, locks):
    source = get_clean_source(driver.page_source)
    text_content_dirty = driver.find_element_by_tag_name("body").text
    text_content = Cleaner.clean_all(text_content_dirty)
    text_content_hash = get_source_hash(text_content)
    duplicate_page = coredb.get_page_with_hash(text_content_hash)
    if duplicate_page is not None:
        logging.debug('Duplicate page found with url: ' + duplicate_page['url'])
        # TODO: add column to db to list which page it's duplicate off
        coredb.update_page(page['id'], PageType.DUPLICATE.value, 200, None, None, duplicate_page['id'])
        return

    links = get_links_from_page(driver, source)
    for url in links:
        handle_new_link(coredb, config, url, page['id'], locks)

    #imgs = driver.find_elements_by_xpath('//img[@src]')
    #img_srcs = set([img.get_attribute('src') for img in imgs])
    #for img_src in img_srcs:
        #if ',' in img_src:
            #continue  # for example svg+xml, ....
        #handle_new_image(coredb, page['id'], img_src)

    coredb.update_page(page['id'], PageType.HTML.value, 200, text_content, text_content_hash)


def process_binary_page(coredb, driver, page, content_type):
    coredb.update_page(page['id'], PageType.BINARY.value, 200)
    coredb.add_page_data(page['id'], content_type)


def parse_page(coredb, driver, page, config, locks):
    # Extract status code and page type
    status_code, content_type = get_status_code_and_content_type(driver)

    # Remove old request history
    del driver.requests

    try:
        driver.get(page['url'])
    except:
        logging.debug("Error on: {}".format(page['url']))
        coredb.update_page(page['id'], None, None)
        return
    time.sleep(PAGE_GET_SLEEP_SECONDS)

    # Extract status code and page type
    status_code, content_type_new = get_status_code_and_content_type(driver)

    if status_code != 204:
        content_type = content_type_new

    if status_code is None:
        logging.warning("Server did not respond on {}".format(page['url']))
        coredb.update_page(page['id'], None, None)
        return

    if status_code < 200 or status_code > 210:
        if content_type is not None and content_type == 'html':
            coredb.update_page(page['id'], 'HTML', status_code)
        else:
            coredb.update_page(page['id'], 'BINARY', status_code)
    else:
        process_html_page(coredb, driver, page, config, locks)