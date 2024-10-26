import logging

from bs4 import BeautifulSoup
from requests import RequestException

from exceptions import ParserFindTagException


def get_response(session, url, encoding='utf-8'):
    response = session.get(url)
    if response is None:
        raise RequestException
    response.encoding = encoding
    return response


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}, {soup}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def create_bsoup_from_url(session, url_constant):
    try:
        response = get_response(session, url_constant)
    except RequestException as e:
        logging.exception(
            f'Ошибка парсера: вызвано исклчение {e.__class__.__name__} '
        )
        return
    return BeautifulSoup(response.text, features='lxml')
