import html
import re

from bs4 import BeautifulSoup


class Cleaner:
    @staticmethod
    def clean_all(text):
        text = Cleaner.clean_html_tags(text)
        text = Cleaner.clean_multiple_spaces(text)
        text = Cleaner.clean_multiple_newlines(text)
        return text

    @staticmethod
    def clean_html_tags(text):
        return BeautifulSoup(text, "lxml").text.strip()

    @staticmethod
    def clean_multiple_spaces(text):
        return ' '.join(text.split())

    @staticmethod
    def clean_multiple_newlines(text):
        return re.sub(r"\n+(?=\n)", "\n", text)