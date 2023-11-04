import uuid
from datetime import datetime, timedelta
from json import dumps

from quarter_lib.logging import setup_logging
from telegram import Update

from services.bookmark_service import get_bookmark_transcriptions
from services.todoist_service import run_todoist_sync_commands
from services.xml_service import xml_to_dict

logger = setup_logging(__file__)


async def handle_xml(file_path, file_name, update: Update):
    xml = open(file_path, "r", encoding="utf-8").read()  # Read file
    xml_dict = await xml_to_dict(xml, update)
    transcribed_bookmarks, title, author = await get_bookmark_transcriptions(xml_dict, update.message.caption,
                                                                             update)
    now = datetime.now()

    command_list = []
    due_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    for transcribed_bookmark in transcribed_bookmarks:
        content = transcribed_bookmark["title"] + " - add highlight to Zotero"

        if "timestamp" in transcribed_bookmark and transcribed_bookmark["timestamp"] is not None:
            recording_timestamp = transcribed_bookmark["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        else:
            recording_timestamp = None
        description_dict = {
            "recognized_text_de": transcribed_bookmark["de"],
            "recognized_text_de_confidence": transcribed_bookmark["de_confidence"],
            "recognized_text_en": transcribed_bookmark["en"],
            "recognized_text_en_confidence": transcribed_bookmark["en_confidence"],
            "recording_timestamp": recording_timestamp,
            "author": author,
            "title": title,
            "file_name": file_name,
            "file_position": transcribed_bookmark["file_position"],
            "annotation": transcribed_bookmark["annotation"],
        }
        desc = dumps(description_dict, indent=4, sort_keys=True, ensure_ascii=False).encode('utf8').decode()
        generated_temp_id = "_" + str(uuid.uuid4())
        command_list.append(
            {
                "type": "item_add",
                "temp_id": generated_temp_id,
                "args": {"content": content, "description": desc,
                         "project_id": "2281154095",
                         "due": {'date': due_date}},
            }
        )
        command_list.append(
            {
                "type": "note_add",
                "args": {"content": "",
                         "item_id": generated_temp_id,
                         "file_attachment":
                             {
                                 "file_name": transcribed_bookmark['upload_result']['file_name'],
                                 "file_size": transcribed_bookmark['upload_result']['file_size'],
                                 "file_type": transcribed_bookmark['upload_result']['file_type'],
                                 "file_url": transcribed_bookmark['upload_result']['file_url'],
                             },
                         }
            }
        )

    command_list = [command for command in command_list if command["type"] != "note_add"]
    sync_command_results = run_todoist_sync_commands(command_list)
    if sync_command_results.status_code != 200:
        logger.error("Error while adding to Todoist")
        raise Exception("Error while adding to Todoist " + sync_command_results.text)
    logger.info(sync_command_results)
    message = "Transcribed {} bookmarks for {} by {}".format(
        len(transcribed_bookmarks), title, author) + " and added them to Todoist"

    logger.info(message)
    return message
