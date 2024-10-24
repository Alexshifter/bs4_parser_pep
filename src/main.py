# main.py
import logging
import re
import requests_cache
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from outputs import control_output
from constants import BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, MAIN_PEPS_URL
from utils import get_response, find_tag


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        # Если основная страница не загрузится, программа закончит работу.
        return
    # Создание "супа".
    soup = BeautifulSoup(response.text, features='lxml')
    # Шаг 1-й: поиск в "супе" тега section с нужным id. Парсеру нужен только
    # первый элемент, поэтому используется метод find().
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    # Шаг 2-й: поиск внутри main_div
    # следующего тега div с классом toctree-wrapper.
    # Здесь тоже нужен только первый элемент, используется метод find().
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    # Шаг 3-й: поиск внутри div_with_ul всех элементов
    # списка li с классом toctree-l1.
    # Нужны все теги, поэтому используется метод find_all().
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            # Если страница не загрузится,
            # программа перейдёт к следующей ссылке.
            continue
        soup = BeautifulSoup(response.text, features='lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))
    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    # Перебор в цикле всех найденных списков.
    for ul in ul_tags:
        # Проверка, есть ли искомый текст в содержимом тега.
        if 'All versions' in ul.text:
            # Если текст найден, ищутся все теги <a> в этом списке.
            a_tags = ul.find_all('a')
            # Остановка перебора списков.
            break
        # Если нужный список не нашёлся,
        # вызывается исключение и выполнение программы прерывается.
    else:
        raise Exception('Ничего не нашлось')
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    # Шаблон для поиска версии и статуса:
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    # Цикл для перебора тегов <a>, полученных ранее.
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
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    table_tag = soup.find('table', class_='docutils')
    pdf_a4_tag = table_tag.find('a', {'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    print(archive_url)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    response = get_response(session, MAIN_PEPS_URL)
    print(EXPECTED_STATUS)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    # Выбираем секцию с табилцами.
    section_tag = find_tag(soup, 'section', attrs={'id': 'index-by-category'})
    # Ищем все теги со статусами PEP.
    abbr_tags = section_tag.find_all('abbr')
    # Ищем все теги с ссылками на страницы PEP.
    links_tags = section_tag.find_all('a', class_='pep reference internal')
    # Создаем 2 списка: статусов и ссылок на PEP.
    abbr_list = [abbr.text for abbr in abbr_tags]
    links_list_with_dublicates = [link['href'] for link in links_tags]
    # Удаляем дубликаты.
    links_list = list(dict.fromkeys(links_list_with_dublicates))
    # Создаем список кортежей вида (статус, полная ссылка).
    abbr_links_list = [
        (
            abbr_list[i], urljoin(MAIN_PEPS_URL, links_list[i])
        ) for i in range(len(links_list))
    ]
    total_peps = 0
    dict_statuses = dict()
    results = [('Статус', 'Количество',)]
    for element in tqdm(abbr_links_list):
        response = get_response(session, element[1])
        if response is None:
            continue
        soup = BeautifulSoup(response.text, features='lxml')
        dl_tag = soup.find('dl')
        dd_tag = dl_tag.dd
        while not dd_tag.abbr:
            # Ищем тег с информацией о статусе, проходя по 'dd'.
            dd_tag = dd_tag.find_next_sibling('dd')
        status_pep = dd_tag.string
        # Проверяем соответствие статусов.
        if status_pep not in EXPECTED_STATUS[element[0][1:]]:
            # Выводим в лог.
            logging.info(
                f'Несовпадающие статусы:\n{element[1]}\n'
                f'Статус в карточке: {status_pep}\n'
                f'Ожидаемые статусы: {EXPECTED_STATUS[element[0][1:]]}')
        if status_pep in dict_statuses:
            # Считаем количество статусов, данные вносим в словарь.
            dict_statuses[status_pep] += 1
        else:
            dict_statuses[status_pep] = 1
        total_peps += 1
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
    # Запускаем функцию с конфигурацией логов.
    configure_logging()
    # Отмечаем в логах момент запуска программы.
    logging.info('Парсер запущен!')
    # Конфигурация парсера аргументов командной строки —
    # передача в функцию допустимых вариантов выбора.
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    # Считывание аргументов из командной строки.
    args = arg_parser.parse_args()
    # Логируем переданные аргументы командной строки.
    logging.info(f'Аргументы командной строки: {args}')
    # Создание кеширующей сессии.
    session = requests_cache.CachedSession()
    # Если был передан ключ '--clear-cache', то args.clear_cache == True.
    if args.clear_cache:
        # Очистка кеша.
        session.cache.clear()
    # Получение из аргументов командной строки нужного режима работы.
    parser_mode = args.mode
    # Поиск и вызов нужной функции по ключу словаря.
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        # передаём их в функцию вывода вместе с аргументами командной строки.
        control_output(results, args)
    # Логируем завершение работы парсера.
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
