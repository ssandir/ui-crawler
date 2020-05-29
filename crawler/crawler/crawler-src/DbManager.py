import psycopg2
from ConfigManager import ConfigManager
import logging


class DbManager:
    def __init__(self):
        self.conn = None

    def execute_query(self, query, params, commit=False):
        if self.conn is None:
            self.connect()
        cur = self.conn.cursor()
        try:
            cur.execute(query, params)
            if commit:
                self.conn.commit()
        except Exception as e:
            logging.error(e)
            self.conn.rollback()
            return

    "Use params as %s in query and in format (value1, value2, ...)"
    def execute_query_fetchall(self, query, params, commit=False):
        if self.conn is None:
            self.connect()
        cur = self.conn.cursor()
        try:
            cur.execute(query, params)
            if commit:
                self.conn.commit()
            return cur.fetchall()
        except Exception as e:
            logging.error(e)
            self.conn.rollback()
            return

    def execute_query_fetchone(self, query, params, commit=False):
        if self.conn is None:
            self.connect()
        cur = self.conn.cursor()
        try:
            cur.execute(query, params)
            if commit:
                self.conn.commit()
            return cur.fetchone()
        except Exception as e:
            logging.error(e)
            self.conn.rollback()
            return

    def connect(self):
        try:
            cm = ConfigManager()
            params = cm.get_db_params()
            logging.debug("Connecting to PostgreSQL server...")
            self.conn = psycopg2.connect(**params)
            self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ)
            logging.debug("Successfully connected to PostgreSQL server!")
        except (Exception, psycopg2.DatabaseError) as error:
            logging.error(error)
