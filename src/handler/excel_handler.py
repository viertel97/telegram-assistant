import os

import numpy as np
import pandas as pd
from loguru import logger

from src.services.strong_service import update_strong_entries

logger.add(
	os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
	format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
	backtrace=True,
	diagnose=True,
)


async def handle_excel(file_path, file_name, update):
	logger.info(file_path)
	if "strong" in file_name:
		done_message = handle_strong(file_path)
		await update.message.reply_text(done_message)
	else:
		logger.error("unsupported handle_excel name: " + file_name)
		await update.message.reply_text("unsupported handle_excel name: " + file_name)


def handle_strong(file_path):
	logger.info("start handle_strong")
	daily_record, unique_sessions = read_strong_excel(file_path)
	done_message = update_strong_entries(daily_record, unique_sessions)
	os.remove(file_path)
	logger.info("stop handle_strong")
	return done_message


def read_strong_excel(file_path):
	df = pd.read_csv(file_path, sep=";")
	df.rename({"Weight (kg)": "Weight"}, axis=1, inplace=True)
	df.rename({"Distance (meters)": "Distance"}, axis=1, inplace=True)
	df.rename({"Duration (sec)": "Workout Duration"}, axis=1, inplace=True)

	if df["Workout Duration"].dtype != "O":
		df["Workout Duration"] = df["Workout Duration"].apply(lambda x: str(round(x / 60, 0)) + "m")
	try:
		df.Weight = df.Weight.str.replace(",", ".")
	except:
		pass
	df.Weight = df.Weight.astype(float)
	try:
		df.RPE = df.RPE.str.replace(",", ".")
	except:
		pass
	df.RPE = df.RPE.astype(float)
	# df.Distance = df.Distance.str.replace(",", ".")
	# df.Distance = df.Distance.astype(float)

	if "Weight Unit" not in df.columns:
		df["Weight Unit"] = "kg"
	if "Distance Unit" not in df.columns:
		df["Distance Unit"] = None

	if "Workout #" in df.columns:
		df.drop("Workout #", axis=1, inplace=True)

	df = df.replace({np.nan: None})
	df = df.where(pd.notnull(df), None)
	df = df.reindex(sorted(df.columns), axis=1)

	return df.values.tolist(), len(df["Date"].unique())
