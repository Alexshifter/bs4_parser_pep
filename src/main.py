import logging
import re
from urllib.parse import urljoin

import requests_cache
from requests import RequestException
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (BASE_DIR, DOWNLOADS, EXPECTED_STATUS, MAIN_DOC_URL,
                       MAIN_PEPS_URL)
from exceptions import ParserFindTagException
from outputs import control_output
from utils import add_msgs_to_logs, create_bsoup_from_url, find_tag


def whats_new(session):
    """Формирует список с ссылками на актуальные
    статьи об изменениях в версиях Python.
    """
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = create_bsoup_from_url(session, whats_new_url)
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    err_msg_list = []
    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        try:
            soup = create_bsoup_from_url(session, version_link)
        except RequestException as e:
            err_msg = (f'Страница {version_link} не загрузилась. '
                       f'Вызвано исключение {e.__class__.__name__}. '
                       f'Переход к следующей.')
            err_msg_list.append(err_msg)
            continue
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))
    if err_msg_list:
        add_msgs_to_logs(err_msg_list, logging.error)
    return results


def latest_versions(session):
    """Формирует список с версиями Python, их статусом и
    ссылкой на документацию.
    """
    soup = create_bsoup_from_url(session, MAIN_DOC_URL)
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise ParserFindTagException('Список версий Python не найден')
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag.get('href')
        pat = re.search(pattern, a_tag.text)
        if pat:
            version = pat.group('version')
            status = pat.group('status')
        else:
            version = a_tag.text
            status = ''
        results.append((link, version, status))
    return results


def download(session):
    """Функция загружает последнюю версию Python."""
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = create_bsoup_from_url(session, downloads_url)
    table_tag = soup.find('table', class_='docutils')
    pdf_a4_tag = table_tag.find('a', {'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    download_dir = BASE_DIR / DOWNLOADS
    download_dir.mkdir(exist_ok=True)
    archive_path = download_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    """Функция считает количество PEP в каждом статусе и формирует таблицу."""
    soup = create_bsoup_from_url(session, MAIN_PEPS_URL)
    section_tag = find_tag(soup, 'section', attrs={'id': 'index-by-category'})
    abbr_tags = section_tag.find_all('abbr')
    links_tags = section_tag.find_all('a', class_='pep reference internal')
    abbr_list = [abbr.text for abbr in abbr_tags]
    links_list_with_dublicates = [link['href'] for link in links_tags]
    links_list = list(dict.fromkeys(links_list_with_dublicates))
    abbr_links_list = [
        (
            abbr_list[i], urljoin(MAIN_PEPS_URL, links_list[i])
        ) for i in range(len(links_list))
    ]
    total_peps = 0
    dict_statuses = dict()
    results = [('Статус', 'Количество',)]
    err_msg_list = []
    incorrect_status_msgs = []
    for element in tqdm(abbr_links_list):
        try:
            soup = create_bsoup_from_url(session, element[1])
        except RequestException as e:
            err_msg = (f'Страница PEP {element[1]} не загрузилась. '
                       f'Вызвано исключение {e.__class__.__name__}. '
                       f'Переход к следующему PEP.')
            err_msg_list.append(err_msg)
            continue
        dl_tag = soup.find('dl')
        dd_tag = dl_tag.dd
        while not dd_tag.abbr:
            dd_tag = dd_tag.find_next_sibling('dd')
        status_pep = dd_tag.string
        if status_pep not in EXPECTED_STATUS[element[0][1:]]:
            inc_status_msg = (
                f'Несовпадающие статусы:\n{element[1]}\n'
                f'Статус в карточке: {status_pep}\n'
                f'Ожидаемые статусы: {EXPECTED_STATUS[element[0][1:]]}'
            )
            incorrect_status_msgs.append(inc_status_msg)
        dict_statuses[status_pep] = dict_statuses.get(status_pep, 0) + 1
        total_peps += 1
    if err_msg_list:
        add_msgs_to_logs(err_msg_list, logging.error)
    if incorrect_status_msgs:
        add_msgs_to_logs(incorrect_status_msgs, logging.info)
    results.extend(list(dict_statuses.items()))
    results.append(('Total', total_peps,))
    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep
}


def main():
    try:
        configure_logging()
        logging.info('Парсер запущен!')
        arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
        args = arg_parser.parse_args()
        logging.info(f'Аргументы командной строки: {args}')
        session = requests_cache.CachedSession()
        if args.clear_cache:
            session.cache.clear()
        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)
        if results is not None:
            control_output(results, args)

    except Exception as e:
        logging.exception(
            f'Ошибка парсера: вызвано исключение {e.__class__.__name__}',
            stack_info=True
        )
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
