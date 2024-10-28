import logging

from bs4 import BeautifulSoup
from requests import RequestException

from exceptions import ParserFindTagException, ResponseIsNoneException


def get_response(session, url, encoding='utf-8'):
    try:
        response = session.get(url)
    except RequestException as e:
        raise ResponseIsNoneException(
            f'Страница PEP {url} не загрузилась. '
            f'Вызвано исключение {e.__class__.__name__}. '
            'Переход к следующему PEP.')
    response.encoding = encoding
    return response


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}, {soup}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def create_bsoup_from_url(session, url_constant, encoding='utf-8'):
    response = get_response(session, url_constant, encoding)
    return BeautifulSoup(response.text, features='lxml')


def add_msgs_to_logs(msg_list, log_method):
    for msg in msg_list:
        log_method(msg)
