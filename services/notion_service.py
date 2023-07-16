import asyncio
import json
import os
import time

import requests
from quarter_lib_old.notion import BASE_URL, HEADERS, get_database
from telegram import Update
from telegram.ext import CallbackContext

from helper.config_helper import is_not_correct_chat_id
from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)
TPT_ID = "b3042bf44bd14f40b0167764a0107c2f"


def update_priority(page_id_priority):
    url = BASE_URL + "pages/" + page_id_priority[0]
    data = {"properties": {"Priority": {"number": page_id_priority[1]}}}
    r = requests.patch(url, data=json.dumps(data), headers=HEADERS)
    if r.status_code != 200:
        print(r.status_code)
        print(r.text)
    return r


async def stretch_TPT(update: Update, context: CallbackContext):
    if is_not_correct_chat_id(update.message.chat_id):
        await update.message.reply_text("Nah")
        return
    await update.message.reply_text("stretching TPT")
    df = get_database(TPT_ID)
    await update.message.reply_text("got TPT", disable_notification=True)
    df["title"] = df["properties~Name~title"].apply(lambda x: x[0]["plain_text"])
    df.drop(columns=["properties~Name~title"], inplace=True)
    df = df[
        ["id", "title", "properties~Priority~number", "properties~Completed~date~start", "properties~Obsolet~checkbox"]
    ]
    df.sort_values(by="properties~Priority~number", inplace=True)
    df = df[df["properties~Obsolet~checkbox"] == False]
    df = df[df["properties~Completed~date~start"].isna()]
    df = df[df["properties~Priority~number"] > 0]
    df.reset_index(drop=True, inplace=True)
    await update.message.reply_text("filtered TPT & starting to update", disable_notification=True)
    for index, row in df.iterrows():
        update_priority((df.iloc[index]["id"], index + 1))
        if (index + 1) % 10 == 0:
            logger.info(f"updated {index + 1} rows")
        if (index + 1) % 30 == 0:
            await update.message.reply_text(f"updated {index + 1} rows", disable_notification=True)
        time.sleep(1)
    await update.message.reply_text("Done")
