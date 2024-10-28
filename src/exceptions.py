from requests import RequestException


class ParserFindTagException(Exception):
    """Вызывается, когда парсер не может найти тег."""


class ParserFindTextException(Exception):
    """Вызывается, когда парсер не может найти содержимое внутри тега."""


class ResponseIsNoneException(RequestException):
    """Вызывается в случае невозможности получить response."""
