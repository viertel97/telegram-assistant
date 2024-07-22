import requests
from quarter_lib.logging import setup_logging
from telegram import Update
from telegram.ext import CallbackContext

from helper.config_helper import is_not_correct_chat_id

logger = setup_logging(__file__)


def process_arguments(arguments):
    processed_list = []
    temp_list = []
    inside_quotes = False

    for item in arguments:
        if '"' in item:
            if inside_quotes:
                temp_list.append(item.replace('"', ''))
                processed_list.append(' '.join(temp_list))
                temp_list = []
                inside_quotes = False
            else:
                temp_list.append(item.replace('"', ''))
                inside_quotes = True
        else:
            if inside_quotes:
                temp_list.append(item)
            else:
                if item.isdigit():
                    processed_list.append(int(item))
                else:
                    processed_list.append(item)

    if temp_list:
        processed_list.append(' '.join(temp_list))

    return processed_list

async def add_placeholder_to_splitwise(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    arguments = process_arguments(context.args)
    group_name = arguments[0]
    number_of_placeholder = int(arguments[1])
    response = requests.post(
        "http://splitwise-service.custom.svc.cluster.local:80/add_placeholder_to_group",
        json={"group_name": group_name, "number_of_placeholder": number_of_placeholder},
    )
    if response.status_code == 200:
        await update.message.reply_text("Placeholder added to splitwise")
    else:
        await update.message.reply_text("Error adding placeholder to splitwise")
