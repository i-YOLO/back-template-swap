import logging
from colorama import init, Fore, Style
from typing_extensions import Annotated, Doc
import sys


init()


class Formatter(logging.Formatter):
    __COLORS__ = {
        logging.CRITICAL: Fore.RED,
        logging.ERROR: Fore.LIGHTRED_EX,
        logging.WARNING: Fore.YELLOW,
        logging.INFO: Fore.LIGHTGREEN_EX,
        logging.DEBUG: Fore.LIGHTBLUE_EX,
        logging.NOTSET: Fore.WHITE,
    }

    def __init__(
        self,
        ecosystem: Annotated[bool, Doc("是否打印运行环境")] = False,
        index: Annotated[bool, Doc("是否打印运行位置")] = False,
        datefmt: str | None = None
    ) -> None:
        self.datefmt = datefmt
        self._fmt = '[%(name)s][%(levelname)s][%(asctime)s]%(message)s'
        self._style = logging.PercentStyle(self._fmt)
        self._index = index
        self._ecosystem = ecosystem

    @staticmethod
    def ensure_once_linebreak(message: str) -> str:
        if message[-1] != '\n':
            return f'{message}\n'
        return message

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        record.asctime = self.formatTime(record, self.datefmt)
        for levelno, _color in self.__COLORS__.items():
            if record.levelno >= levelno:
                color = _color
                break
        else: color = Fore.WHITE
        message = f'{color}{record.message}{Style.RESET_ALL}'
        levelname = f'{color}{record.levelname}{Style.RESET_ALL}'
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            message = f'{self.ensure_once_linebreak(message)}{Fore.RED}{record.exc_text}{Style.RESET_ALL}'
        if record.stack_info:
            message = f'{self.ensure_once_linebreak(message)}{Fore.RED}{record.stack_info}{Style.RESET_ALL}'
        prefix = ''
        if self._ecosystem:
            ecosystemes = [
                f'{record.processName}:{record.process}' if record.processName and record.process else '',
                f'{record.threadName}:{record.thread}' if record.threadName and record.threadName else '',
                record.taskName,
            ]
            prefix = f'[{'-'.join(filter(None, ecosystemes))}]'
        if self._index:
            prefix = f'{prefix}[{record.pathname}:{record.lineno}<{record.funcName}>]'
        return f'[{Fore.LIGHTWHITE_EX}{record.name}{Style.RESET_ALL}][{levelname}][{record.asctime}]{prefix}{message}'


def create_logger(
    name: str,
    level: int = logging.INFO,
    index: bool = False,
    ecosystem: bool = False
) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.formatter = Formatter(index=index, ecosystem=ecosystem)
    logger.addHandler(console_handler)
    logger.setLevel(level)
    return logger
