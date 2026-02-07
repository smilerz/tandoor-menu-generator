import logging
import re
import shelve
import sys
from datetime import datetime, timedelta
from functools import wraps
from uuid import NAMESPACE_OID, uuid3

from tqdm import tqdm
from tzlocal import get_localzone

_caches = None


def _get_caches():
    global _caches
    if _caches is not None:
        return _caches
    try:
        _caches = shelve.open('caches.db', writeback=True)
        keys_to_delete = [k for k in _caches if _caches[k]['expired'] < datetime.now()]
        for key in keys_to_delete:
            _caches.pop(key)
    except Exception:
        _caches = {}
    return _caches


class InfoFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno in (logging.DEBUG, logging.INFO)


class TQDM(tqdm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.step = 0

    def update_step(self, step=1):
        self.step += step
        self.update(step)

    def reset_step(self):
        self.step = 0
        self.n = 0

    def last_step(self):
        self.n = 100


# logging methods
def setup_logging(log='INFO'):
    log_levels = {
        'CRITICAL': logging.CRITICAL,
        'ERROR': logging.ERROR,
        'WARNING': logging.WARNING,
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG
    }
    logger = logging.getLogger('CreateMenu')
    logger.setLevel(logging.DEBUG)

    # Set up the two formatters
    formatter_brief = logging.Formatter(fmt='[%(asctime)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')
    formatter_explicit = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%H:%M:%S'
    )

    # Set up the file logger
    fh = logging.FileHandler(filename='cocktail-menu.log', encoding='utf-8', mode='w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter_explicit)
    logger.addHandler(fh)

    # Set up the error / warning command line logger
    ch_err = logging.StreamHandler(stream=sys.stderr)
    ch_err.setFormatter(formatter_explicit)
    ch_err.setLevel(logging.WARNING)
    logger.addHandler(ch_err)

    # Set up the verbose info / debug command line logger
    ch_std = logging.StreamHandler(stream=sys.stdout)
    ch_std.setFormatter(formatter_brief)
    ch_std.addFilter(InfoFilter())
    level = -1
    if isinstance(log, str):
        try:
            level = log_levels[log.upper()]
        except KeyError:
            pass
    elif isinstance(log, int):
        if 0 <= log <= 50:
            level = log

    if level < 0:
        print('Valid logging levels specified by either key or value:{}'.format('\n\t'.join(
            '{}: {}'.format(key, value) for key, value in log_levels.items()))
        )
        raise RuntimeError('Invalid logging level selected: {}'.format(level))
    else:
        ch_std.setLevel(level)
        logger.addHandler(ch_std)
        logger.loglevel = level
    return logger


def get_log_level(log):
    return log


# utlity methods
def str2bool(v):
    if isinstance(v, bool) or v is None:
        return v
    elif isinstance(v, int) or isinstance(v, float):
        return v == 1
    else:
        return v.lower() in ("yes", "true", "1")


# date methods
def string_to_date(date_str):
    # Define the regex pattern
    pattern = r'^-?\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$'

    # Use re.match to check if the string matches the pattern
    if re.match(pattern, date_str):
        if date_str[:1] == '-':
            return datetime.strptime(date_str[1:], '%Y-%m-%d').replace(tzinfo=get_localzone()), False
        else:
            return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=get_localzone()), True
    else:
        return False, False


def split_offset(s):
    # Define the regex pattern to match the desired format
    pattern = r'^(-?)(\d+)([dD]?[aA]?[yY]?[sS]?)$'

    # Use re.match to extract the parts of the string
    match = re.match(pattern, s)

    if match:
        # Extract and assign values to variables
        after = not match.group(1) == '-'
        offset = int(match.group(2))
        interval = match.group(3).lower()  # Convert to lowercase for case-insensitivity
        return after, offset, interval

    else:
        # Return None or raise an exception for invalid input
        raise ValueError(f"Invalid time offset format: {s}.  Value must be in form of '-XXdays'")


def format_date(string, future=False):
    date, after = string_to_date(string)
    if date:
        return date, after

    after, offset, interval = split_offset(string)
    # TODO support more time intervals that days
    offset = timedelta(days=offset)
    if future:
        return datetime.now(get_localzone()) + offset, after
    return datetime.now(get_localzone()) - offset, after


def printable_date(date, format='short'):
    if format == 'long':
        return date.strftime('%B %d, %Y'), ordinal(date.day)
    elif format == 'medium':
        return date.strftime('%B %d'), ordinal(date.day)
    elif format == 'number':
        return date.strftime('%m/%d'), ordinal(date.day)
    elif format == 'short':
        return date.strftime('%b %d'), ordinal(date.day)
    else:
        return date.strftime('%m/%d/%Y'), ordinal(date.day)


def ordinal(num):
    suffixes = ['th', 'st', 'nd', 'rd']

    remainder = num % 10
    suffix = suffixes[0]  # default to 'th'

    if remainder in [1, 2, 3] and not (11 <= num <= 13):
        suffix = suffixes[remainder]

    return suffix


# decorator methods
def display_progress(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        try:
            progress = self.progress or None
        except AttributeError:
            progress = None
        if progress:
            progress.update_step()
        return result
    return wrapper


def cached(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        caches = _get_caches()
        if (ttl := kwargs.get('ttl', None)) is None:
            try:
                ttl = self.ttl
            except AttributeError:
                ttl = 240
        if not ttl or ttl <= 0:
            return func(self, *args, **kwargs)
        expire_after = timedelta(minutes=ttl)
        # uuid's are consistent across runs, hash() is not
        key = str(uuid3(NAMESPACE_OID, ''.join([str(x) for x in args]) + str(kwargs)))
        if key not in caches or caches[key]['expired'] < datetime.now():
            caches[key] = {'data': func(self, *args, **kwargs), 'expired': datetime.now() + expire_after}
            if hasattr(caches, 'sync'):
                caches.sync()

        return caches[key]['data']
    return wrapper
