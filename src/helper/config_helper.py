import json
import os

from quarter_lib.akeyless import get_secrets

CHAT_ID = get_secrets("telegram/chat_id")


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
