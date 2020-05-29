from DbManager import DbManager
from enum import Enum
import logging

class PageType(Enum):
    HTML = 'HTML'
    BINARY = 'BINARY'
    DUPLICATE = 'DUPLICATE'
    FRONTIER = 'FRONTIER'
    PROCESSING = 'PROCESSING'


class DataType(Enum):
    PDF = 'PDF'
    DOC = 'DOC'
    DOCX = 'DOCX'
    PPT = 'PPT'
    PPTX = 'PPTX'


# file structure:
# lock_next_page
# update_next_page
# lock_server
# get_server_by_ip_address
# get_site_by_domain
# get_sites
# get_page_by_url
# add_server
# add_site
# add_page
# add_link
# update_server_last_visit
# update_page

class CoreDb:
    def __init__(self):
        self.dm = DbManager()

    def lock_next_page(self):
        query = """
            UPDATE crawldb.server ss 
            SET last_visit = (now() at time zone 'utc'), lock = true
            FROM ( 
                SELECT p.id as pid, s.id as sid
                FROM crawldb.page p 
                LEFT JOIN crawldb.site d on p.site_id = d.id
                LEFT JOIN crawldb.server s on d.server_id = s.id
                WHERE s.lock = false AND
                    (now() at time zone 'utc') - s.last_visit > d.delay * (INTERVAL '1 second') AND   
                    p.page_type_code = %s
                ORDER BY p.id ASC
                LIMIT 1
            ) AS subquery
            WHERE ss.id = subquery.sid
            RETURNING subquery.pid, subquery.sid;"""
        pid_sid = self.dm.execute_query_fetchone(query, (PageType.FRONTIER.value,), commit=True)
        logging.debug("Locked (page, server): " + repr(pid_sid))
        return pid_sid

    def update_next_page(self, pid, sid):
        query = """ 
                UPDATE crawldb.page
                SET page_type_code = %s
                WHERE id = %s;
                UPDATE crawldb.server
                SET lock = false
                WHERE id = %s;
                SELECT *
                FROM crawldb.page
                WHERE id = %s;"""
        row = self.dm.execute_query_fetchone(query, (PageType.PROCESSING.value, pid, sid, pid), commit=True)
        logging.debug("Unlocked server and got next page: " + repr(row))
        return CoreDb.format_page_data(row)

    def lock_server(self, id):
        query = """
               UPDATE crawldb.server
               SET lock = true
               WHERE id = %s AND lock = false
               RETURNING last_visit;"""
        last_visit = self.dm.execute_query_fetchone(query, (id,), commit=True)
        logging.debug("Locked server: " + repr(id) + " last visit: " + repr(last_visit))
        return last_visit

    def get_server_by_ip_address(self, ip_address):
        query = 'SELECT * FROM crawldb.server ' \
                'WHERE ip_address = %s ; '
        row = self.dm.execute_query_fetchone(query, (ip_address,))
        logging.debug("Got server by ip address: " + repr(row))
        return None if (row is None) else CoreDb.format_server_data(row)

    def get_site_by_domain(self, domain):
        query = 'SELECT * FROM crawldb.site ' \
                'WHERE domain = %s ; '
        row = self.dm.execute_query_fetchone(query, (domain,))
        logging.debug("Got site by domain: " + repr(row))
        return None if (row is None) else CoreDb.format_site_data(row)

    def get_page_by_url(self, url):
        query = 'SELECT * FROM crawldb.page ' \
                'WHERE url = %s ; '
        row = self.dm.execute_query_fetchone(query, (url,))
        logging.debug("Got page by url: " + repr(url) + " found: " + (repr(row) if row is None else repr(row[0])))
        return None if (row is None) else CoreDb.format_page_data(row)

    def get_page_with_hash(self, html_hash):
        query = """
            SELECT * FROM crawldb.page
            WHERE html_hash = %s
        """
        row = self.dm.execute_query_fetchone(query, (html_hash,))
        return None if (row is None) else CoreDb.format_page_data(row)

    def get_link(self, from_id, to_id):
        query = """
            SELECT * FROM crawldb.link 
            WHERE from_page = %s AND to_page = %s
        """
        row = self.dm.execute_query_fetchone(query, (from_id, to_id))
        return False if (row is None) else True

    def add_server(self, ip_address, last_visit=None):
        query = 'INSERT INTO crawldb.server (ip_address, last_visit, lock) ' \
                'VALUES (%s, %s, false) ' \
                'RETURNING * ; '
        row = self.dm.execute_query_fetchone(query, (ip_address, last_visit), commit=True)
        logging.debug("Added server: " + repr(ip_address))
        return None if (row is None) else CoreDb.format_server_data(row)

    def add_site(self, domain, server_id, robots_content, sitemap_content, delay):
        query = 'INSERT INTO crawldb.site (domain, server_id, robots_content, sitemap_content, delay) ' \
                'VALUES (%s, %s, %s, %s, %s) ' \
                'RETURNING * ; '
        row = self.dm.execute_query_fetchone(query, (domain, server_id, robots_content, sitemap_content, delay), commit=True)
        logging.debug("Added site: " + repr(domain))
        return None if (row is None) else CoreDb.format_site_data(row)

    def add_page(self, site_id, url):
        query = """
            INSERT INTO crawldb.page (site_id, page_type_code, url)
            VALUES (%s, %s, %s)
            RETURNING *;"""
        row = self.dm.execute_query_fetchone(query, (site_id, PageType.FRONTIER.value, url), commit=True)
        logging.debug("Added page: " + repr(url))
        return None if (row is None) else CoreDb.format_page_data(row)

    def add_link(self, from_id, to_id):
        query = """
            INSERT INTO crawldb.link (from_page, to_page)
            VALUES (%s, %s);"""
        self.dm.execute_query(query, (from_id, to_id), commit=True)
        logging.debug("Added link from: " + repr(from_id) + " to: " + repr(to_id))

    def add_img(self, page_id, filename, content_type):
        query = """
            INSERT INTO crawldb.image (page_id, filename, content_type, data, accessed_time)
            VALUES (%s, %s, %s, %s, (now() at time zone 'utc'))
        """
        self.dm.execute_query(query, (page_id, filename, content_type, None), commit=True)
        logging.debug("Added image with full filename: " + "{0}.{1}".format(filename, content_type))

    def add_page_data(self, page_id, content_type):
        query = """
            INSERT INTO crawldb.page_data (page_id, data_type_code, data)
            VALUES (%s, %s, %s)
        """
        self.dm.execute_query(query, (page_id, content_type.value, None), commit=True)
        logging.debug("Added page data for page {}".format(page_id))

    def update_server_last_visit(self, server_id, last_visit):
        query = 'UPDATE crawldb.server ' \
                'SET last_visit = %s, lock = false ' \
                'WHERE id = %s ; '
        self.dm.execute_query(query, (last_visit, server_id), commit=True)
        logging.debug('Updated server: ' + repr(server_id) + ' last visit: ' + repr(last_visit))

    def update_page(self, page_id, page_type, status_code, html_content=None, html_hash=None, duplicate_page_id=None):
        query = """
            UPDATE crawldb.page 
            SET page_type_code = %s, http_status_code = %s, html_content = %s, html_hash = %s, duplicate_page_id = %s, accessed_time=(now() at time zone 'utc')
            WHERE id = %s;
        """
        self.dm.execute_query(
            query,
            (page_type, status_code, html_content, html_hash, duplicate_page_id, page_id),
            commit=True
        )
        logging.debug("Updated page: " + repr((page_id, page_type, status_code)))

    @staticmethod
    def format_server_data(server_row):
        return {
            'id': server_row[0],
            'ip_address': server_row[1],
            'last_visit': server_row[2],
            'lock': server_row[3]
        }

    @staticmethod
    def format_page_data(page_row):
        return {
            'id': page_row[0],
            'site_id': page_row[1],
            'page_type_code': page_row[2],
            'url': page_row[3],
            'html_content': page_row[4],
            'html_hash': page_row[5],
            'duplicate_page_id': page_row[6],
            'http_status_code': page_row[7],
            'accessed_time': page_row[8]
        }

    @staticmethod
    def format_site_data(site_row):
        return {
            'id': site_row[0],
            'domain': site_row[1],
            'server_id': site_row[2],
            'robots_content': site_row[3],
            'sitemap_content': site_row[4],
            'delay': site_row[5]
        }
