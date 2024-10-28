from pathlib import Path

# Константы директорий.
BASE_DIR = Path(__file__).parent
DOWNLOADS = 'downloads'
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'parser.log'
RESULTS = 'results'

# Константы URL.
MAIN_DOC_URL = 'https://docs.python.org/3/'
MAIN_PEPS_URL = 'https://peps.python.org/'

# Шаблон формата логов:
# Время записи – Уровень сообщения – Cообщение.
LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'
DT_FORMAT = '%d.%m.%Y %H:%M:%S'

# Шаблон даты для добавления в имя файла.
DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'

# PEP статусы.
EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}

# Аргументы для вывода информации.
OUTPUT_PRETTY_TABLE = 'pretty'
OUTPUT_FILE = 'file'
