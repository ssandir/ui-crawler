from web_manager import parse_page, init_selenium
from CoreDb import CoreDb
import threading
import time
import logging


NUM_OF_TRIES = 50
NUM_OF_DRIVER_REQUESTS = 5


class Worker(threading.Thread):
    locks = {
        'server': threading.Lock(),
        'site': threading.Lock(),
        'page': threading.Lock(),
        'get': threading.Lock()
    }

    def __init__(self, config, *args):
        super(Worker, self).__init__(*args)
        self.driver = init_selenium()
        self.config = config
        self.coredb = CoreDb()
        logging.debug("Thread created")

    def __del__(self):
        self.driver.close()
        logging.warning("-- Thread destroyed")

    def run(self):
        selenium_counter = 0
        while True:
            for _ in range(NUM_OF_TRIES):
                with Worker.locks['get']:
                    pid_sid = self.coredb.lock_next_page()
                    if pid_sid is not None:
                        page = self.coredb.update_next_page(pid_sid[0], pid_sid[1])
                        break
                time.sleep(1)
            else:
                logging.warning("No more work, stopping...")
                break

            if selenium_counter == NUM_OF_DRIVER_REQUESTS:
                logging.warning("Reseting selenium webdriver...")
                self.driver.quit()
                self.driver = init_selenium()
                time.sleep(2)
                selenium_counter = 0

            try:
                logging.warning("Worker on: {3}: {0} [{1}/{2}]".format(page['url'], selenium_counter + 1, NUM_OF_DRIVER_REQUESTS, page['id']))
                parse_page(self.coredb, self.driver, page, self.config, Worker.locks)
                selenium_counter += 1
            except Exception as e:
                selenium_counter += 1
                logging.error(e)
