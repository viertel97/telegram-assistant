from json import dumps
import pandas as pd

from quarter_lib.logging import setup_logging
from telegram import Update

from src.handler.pdf_handler import handle_pdf_during_xml_processing, filter_content
from src.services.book_note_service import get_smallest_project
from src.services.bookmark_service import prepare_bookmark_transcriptions, get_bookmark_transcriptions, \
    remove_duplicated_bookmarks
from src.services.logging_service import log_to_telegram
from src.services.todoist_service import get_rework_projects, get_items_by_todoist_project, add_comment_with_file_attachment
from todoist_api_python.api import TodoistAPI
from quarter_lib.akeyless import get_secrets
from src.services.xml_service import xml_to_dict
logger = setup_logging(__file__)

async def handle_xml(file_path, file_name, update: Update):
    xml = open(file_path, encoding="utf-8").read()  # Read file
    xml_dict = await xml_to_dict(xml, update)
    prepared_bookmarks, title, author = prepare_bookmark_transcriptions(xml_dict, update.message.caption)

    projects = get_rework_projects("Book-Notes")
    tasks = [tasks for project in projects for tasks in get_items_by_todoist_project(project.id)]
    tasks = [filter_content(task.__dict__) for task in tasks]

    de_duplicated_bookmarks = remove_duplicated_bookmarks(prepared_bookmarks, tasks, title, author)
    await log_to_telegram(f"Found {len(de_duplicated_bookmarks)} new bookmarks for {title} by {author} (duplicates: {len(prepared_bookmarks) - len(de_duplicated_bookmarks)})", logger, update)

    if de_duplicated_bookmarks:
        transcribed_bookmarks = await get_bookmark_transcriptions(de_duplicated_bookmarks, update.message.caption, title, author, update)

        project, min_size, idx = get_smallest_project("Book-Notes")
        await log_to_telegram(
            f"List {idx + 1} ({project.id}) was chosen as the smallest project with {min_size} items",
            logger,
            update,
        )

        # Initialize Todoist API
        todoist_token = get_secrets("todoist/token")
        todoist_api = TodoistAPI(todoist_token)

        # Process each bookmark using the new REST API
        for transcribed_bookmark in transcribed_bookmarks:
            content = transcribed_bookmark["title"] + " - add highlight to Zotero"

            if "timestamp" in transcribed_bookmark and transcribed_bookmark["timestamp"] is not None and not pd.isna(transcribed_bookmark["timestamp"]):
                recording_timestamp = transcribed_bookmark["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            else:
                recording_timestamp = None

            description_dict = {
                "recognized_text_de": transcribed_bookmark["de"],
                "recognized_text_en": transcribed_bookmark["en"],
                "recording_timestamp": recording_timestamp,
                "author": author,
                "title": title,
                "bookmark_file_name": file_name,
                "file_name": transcribed_bookmark["file_name"],
                "file_position": transcribed_bookmark["file_position"],
                "annotation": transcribed_bookmark["annotation"],
            }
            desc = dumps(description_dict, indent=4, sort_keys=True, ensure_ascii=False).encode("utf8").decode()

            try:
                # Create task using the REST API
                task = todoist_api.add_task(
                    content=content,
                    description=desc,
                    project_id=project.id,
                )
                logger.info(f"Created task {task.id} for bookmark: {content}")

                # Add comment with file attachment using the new REST API
                add_comment_with_file_attachment(
                    task_id=task.id,
                    file_upload_result=transcribed_bookmark["upload_result"],
                    content="",
                )
                logger.info(f"Added file attachment to task {task.id}")

            except Exception as e:
                logger.error(f"Error while adding bookmark to Todoist: {str(e)}")
                raise Exception(f"Error while adding to Todoist: {str(e)}")

        message = f"Transcribed {len(transcribed_bookmarks)} bookmarks for {title} by {author}" + " and added them to Todoist"
        logger.info(message)
    else:
        message = f"No new bookmarks to add for {title} by {author}"
        await log_to_telegram(message, logger, update)

    await handle_pdf_during_xml_processing(update.effective_message.caption, title, update)

    return message