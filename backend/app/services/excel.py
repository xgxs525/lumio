import logging

from excel_splitter import ExcelSplitter, setup_logging

_logger = setup_logging('INFO')
_splitter = ExcelSplitter(_logger)


def get_excel_splitter() -> ExcelSplitter:
    return _splitter


def get_logger() -> logging.Logger:
    return _logger
