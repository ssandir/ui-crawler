from pprint import pprint
import logging
from ConfigManager import ConfigManager
from Worker import Worker
from CoreDb import CoreDb
from functions import handle_new_page


def initialize_logger(log_level: str):
    logging_level = logging.getLevelName(log_level)
    logging_format = '%(asctime)s %(module)s:%(lineno)d %(levelname)-8s %(message)s'
    logging.basicConfig(level=logging_level, format=logging_format)


if __name__ == "__main__":
    cm = ConfigManager()
    crawler_config = cm.get_crawler_params()
    initialize_logger(crawler_config['log_level'])

    logging.info('Running with params:')
    pprint(crawler_config)

    seed_urls = crawler_config['seed_urls']
    coredb = CoreDb()
    for url in seed_urls:
        handle_new_page(coredb, url, crawler_config, Worker.locks)

    threads = list()
    for index in range(crawler_config['workers']):
        x = Worker(crawler_config)
        threads.append(x)
        x.start()

    for index, thread in enumerate(threads):
        thread.join()
