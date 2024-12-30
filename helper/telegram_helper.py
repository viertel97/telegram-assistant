import time

from quarter_lib.logging import setup_logging
from telegram.error import NetworkError

logger = setup_logging(__file__)


async def retry_on_error(func, wait=0.1, retry=0, *args, **kwargs):
    i = 0
    while True:
        try:
            return await func(*args, **kwargs)
        except NetworkError as e:
            logger.error(e)
            logger.error(f"Network Error. Retrying...{i}")
            i += 1
            time.sleep(wait)
            if retry != 0 and i == retry:
                break
