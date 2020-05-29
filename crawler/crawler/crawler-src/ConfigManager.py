from configparser import ConfigParser


class ConfigManager:
    def __init__(self, filename='/crawler-src/config.conf'):
        self.parser = ConfigParser()
        self.parser.read(filename)

    def get_db_params(self):
        return {'host': self.parser['DB']['host'],
                'database': self.parser['DB']['database'],
                'user': self.parser['DB']['user'],
                'password': self.parser['DB']['password']}

    def get_crawler_params(self):
        return {'bot_name': self.parser['CRAWLER']['bot_name'],
                'seed_urls': self.parser['CRAWLER']['seed_urls'].split(','),
                'workers': int(self.parser['CRAWLER']['workers']),
                'request_delay': int(self.parser['CRAWLER']['request_delay']),
                'selenium_timeout': int(self.parser['CRAWLER']['selenium_timeout']),
                'chromedriver_path': self.parser['CRAWLER']['chromedriver_path'],
                'log_level': self.parser['CRAWLER']['log_level']}
