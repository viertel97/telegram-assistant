import os

from loguru import logger
from services.book_note_service import add_tasks, get_tasks, read_markdown

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)


def handle_markdown(file_path, file_name, update):
    logger.info("start handle_markdown")
    soup = read_markdown(file_path)
    logger.info("read_markdown done")
    logger.info("start get_tasks")
    tasks, message = get_tasks(soup, os.path.splitext(file_name)[0])
    logger.info("get_tasks done")
    logger.info("start add_tasks")
    try:
        message = add_tasks(tasks, message)
    except Exception as e:
        logger.error(e)
        return str(e)

    logger.info("add_tasks done")
    return message
