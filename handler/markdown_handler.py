import os

from services.book_note_service import add_tasks, get_tasks, read_markdown
from quarter_lib.logging import setup_logging

from services.logging_service import log_to_telegram

logger = setup_logging(__file__)


async def handle_markdown(file_path, file_name, update):
    logger.info("start handle_markdown")
    soup = read_markdown(file_path)
    logger.info("read_markdown done")
    logger.info("start get_tasks")
    tasks, number_of_tasks, number_of_comments, title = get_tasks(soup, os.path.splitext(file_name)[0])
    message = "{len} annotations with {comments} comments were found in '{title}' and will now be added to Todoist".format(
        len=number_of_tasks, comments=number_of_comments, title=title)
    await log_to_telegram(message, logger, update)
    logger.info("get_tasks done")
    logger.info("start add_tasks")
    await add_tasks(tasks, message, update)
    logger.info("add_tasks done")
    return message
