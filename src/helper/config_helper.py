import json
import os

import requests
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

from src.helper.caching import ttl_cache


logger = setup_logging(__file__)

CHAT_ID = get_secrets("telegram/chat_id")

MASTER_KEY, BOOK_PATH_MAPPING_BIN = get_secrets(
    [
        "jsonbin/masterkey",
        "jsonbin/book_path_mapping-bin",
    ]
)
BASE_URL = "https://api.jsonbin.io/v3"
BOOK_PATH_MAPPING_URL = f"{BASE_URL}/b/{BOOK_PATH_MAPPING_BIN}"


@ttl_cache(ttl=60 * 60)
def get_book_path_mapping_from_web():
    logger.info("getting rework data from web")
    response = requests.get(
        BOOK_PATH_MAPPING_URL + "/latest",
        headers={"User-Agent": "Mozilla/5.0", "X-Master-Key": MASTER_KEY},
    )
    return response.json()["record"]

# update book_path_mapping
def update_book_path_mapping(book_path_mapping):
    logger.info("updating book path mapping")
    response = requests.put(
        BOOK_PATH_MAPPING_URL,
        headers={"User-Agent": "Mozilla/5.0", "X-Master-Key": MASTER_KEY, "Content-Type": "application/json"},
        json=book_path_mapping,
    )
    if response.status_code == 200:
        logger.info("Book path mapping updated successfully")
    else:
        logger.error(f"Failed to update book path mapping: {response.text}")

def is_not_correct_chat_id(chat_id):
    return str(chat_id) != CHAT_ID


def get_config(file_path):
    with open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)) + "/config/",
            file_path,
        ),
        encoding="utf-8",
    ) as f:
        data = json.load(f)
    return data


def get_config_as_dict(file_path):
    databases = get_config(file_path)
    databases_dict = {}
    for database in databases:
        key = list(database.keys())[0]
        databases_dict[(key)] = database[key]
    return databases_dict


def get_value(value, row, config):
    return next(i for i in config if i[row] == value)
