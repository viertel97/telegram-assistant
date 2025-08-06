import json
import os
import re
import tempfile

import fitz
import pandas as pd
from quarter_lib.logging import setup_logging
from telegram import Update

from src.helper.config_helper import get_book_path_mapping_from_web
from src.helper.file_helper import delete_files
from src.services.logging_service import log_to_telegram
from src.services.microsoft_service import download_file_from_path, replace_file_in_onedrive, download_pdf_from_path
from src.services.todoist_service import (
	get_items_by_todoist_project,
	get_rework_projects,
	run_todoist_sync_commands,
	update_description,
)

logger = setup_logging(__file__)
FINDING_THRESHOLD = 0.75
LANGUAGE = "de"
NUMBER_OF_WORDS_TO_SEARCH = 4


def filter_content(task):
	return task | json.loads(task["description"])


def get_rect(findings):
	x0y0 = findings[0]["text_instances"][0][0]
	x0y1 = findings[0]["text_instances"][0][1]
	x1y0 = findings[0]["text_instances"][0][2]
	x1y1 = findings[0]["text_instances"][0][3]
	return fitz.Rect(x0y0, x0y1, x1y0, x1y1)


def get_filtered_findings(findings):
	page_numbers = [page["page"].number for page in findings]
	proportions = pd.Series(page_numbers).value_counts(normalize=True)
	if proportions.head(1).values[0] > FINDING_THRESHOLD:
		return [page for page in findings if page["page"].number == proportions.head(1).index[0]], page_numbers
	return None, page_numbers


async def handle_pdf(file_path, file_name, update: Update, caption: str = None):
	to_delete = []
	projects = get_rework_projects("Book-Notes")
	tasks = [tasks for project in projects for tasks in get_items_by_todoist_project(project.id)]
	tasks = [filter_content(task.__dict__) for task in tasks]
	df = pd.DataFrame(tasks)
	grouped_df = df.groupby("title")

	# Use provided caption or fall back to update.message.caption
	caption_to_use = caption if caption is not None else update.message.caption
	splitted_caption = caption_to_use.split(" § ")
	selected_book_from_todoist, selected_language = (
		splitted_caption[0],
		splitted_caption[1],
	)
	if selected_book_from_todoist in grouped_df.groups:
		group = grouped_df.get_group(selected_book_from_todoist)
		await log_to_telegram(
			f"found '{len(group)}' tasks for '{selected_book_from_todoist}'",
			logger,
			update,
		)
		document = fitz.open(file_path)
		not_found_counter = 0
		try:
			file_version = int(re.search(r"V[0-9]{1,2}", file_name).group(0)[1:])
		except AttributeError:
			file_version = 1
		id_list = []
		command_list = []
		for _, task in group.iterrows():
			text_to_search = task["recognized_text_" + selected_language]
			logger.info(f"text to search: {text_to_search}")
			split_search_text = text_to_search.split(" ")
			findings = search_for_text_in_document(document, split_search_text)
			logger.info(f"found '{len(findings)}' entries for '{text_to_search}'")
			if len(findings) and text_to_search != "" and text_to_search != " ":
				filtered_findings, page_numbers = get_filtered_findings(findings)
				if filtered_findings:
					try:
						content = await add_annotation_to_finding(filtered_findings, task, text_to_search)
						command_list.append({"type": "item_close", "args": {"id": task.id}})
						id_list.append(task.id)
						await log_to_telegram(
							f"added '{content}' to page numbers '{page_numbers}' for '{len(filtered_findings)}' filtered findings",
							logger,
							update,
						)
					except ValueError as e:
						not_found_counter += 1
						logger.error(e)
						await update_task_with_page_numbers(page_numbers, task)
						await log_to_telegram(
							f"Error while highlighting text '{text_to_search}' on page {page_numbers[0]}.",
							logger,
							update,
						)
				else:
					not_found_counter += 1
					await update_task_with_page_numbers(page_numbers, task)
					await log_to_telegram(
						f"The text '{text_to_search}' was found on different pages [{page_numbers!s}] and can't be highlighted",
						logger,
						update,
					)
			else:
				await log_to_telegram(f"nothing found for '{text_to_search}'", logger, update)
				not_found_counter += 1
		if not_found_counter == len(group):
			await log_to_telegram(f"nothing found for all {len(group)} tasks", logger, update)
			return None

		with tempfile.NamedTemporaryFile(suffix=f"_V{file_version + 1}.pdf", delete=False) as temp_pdf:
			new_file_path = temp_pdf.name

		document.save(new_file_path)
		await update.message.reply_document(
			document=open(new_file_path, "rb"),
			caption=f"'{not_found_counter}' out of possible '{group.shape[0]}' could not have been added - therefore '{group.shape[0] - not_found_counter}' annotations has been added sucecessfully to the PDF '{file_name}'.",
		)
		response = run_todoist_sync_commands(command_list)

		logger.info(f"run_todoist_sync_commands response: {response}")
		if response.status_code != 200:
			await log_to_telegram("Error while syncing todoist", logger, update)
		else:
			await log_to_telegram(f"synced todoist with positive response: {response} - {response.text}", logger, update)

		delete_files(to_delete)
		return new_file_path
	else:
		await log_to_telegram(
			f"no book for the caption '{selected_book_from_todoist}' found",
			logger,
			update,
		)
		delete_files(to_delete)
		return None


async def handle_pdf_during_xml_processing(path_to_identify, title, update: Update):
	"""
	Annotate PDF files directly during XML processing by:
	1. Getting the book path mapping
	2. Finding the corresponding PDF for the XML file
	3. Downloading the PDF from OneDrive
	4. Calling handle_pdf function to process annotations
	5. Updating the file back to OneDrive
	"""
	to_delete = []

	try:
		# Get the book path mapping
		book_path_mapping = get_book_path_mapping_from_web()

		# Find the corresponding PDF path for this XML file
		pdf_path, language = None, None
		for xml_path, language_and_path in book_path_mapping.items():
			if path_to_identify == xml_path:
				pdf_path = language_and_path["onedrive_path"]
				language = language_and_path["language"]
				break

		if not pdf_path:
			await log_to_telegram(
				f"No PDF mapping found for XML file: {path_to_identify}",
				logger,
				update,
			)
			return

		if not language:
			await log_to_telegram(
				f"No language found for PDF mapping: {pdf_path}",
				logger,
				update,
			)
			return

		await log_to_telegram(
			f"Found PDF mapping: {path_to_identify} -> {pdf_path}",
			logger,
			update,
		)

		# Create temporary file for the downloaded PDF
		with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as temp_pdf:
			temp_pdf_path = temp_pdf.name
		to_delete.append(temp_pdf_path)

		# Download the PDF from OneDrive
		try:
			await log_to_telegram(f"Downloading PDF from OneDrive: {pdf_path}", logger, update)
			download_pdf_from_path(pdf_path, temp_pdf_path)
			await log_to_telegram(f"Successfully downloaded PDF to {temp_pdf_path}", logger, update)
		except Exception as e:
			await log_to_telegram(f"Error downloading PDF: {str(e)}", logger, update)
			return

		# Create the caption in the correct format for handle_pdf
		# Format: "book_title § language"
		caption = f"{title} § {language}"

		# Call the existing handle_pdf function with the caption parameter
		pdf_filename = os.path.basename(pdf_path)
		annotated_pdf_path = await handle_pdf(temp_pdf_path, pdf_filename, update, caption)

		# If annotations were successfully added, upload the annotated PDF back to OneDrive
		if annotated_pdf_path:
			to_delete.append(annotated_pdf_path)
			try:
				await log_to_telegram(f"Uploading annotated PDF back to OneDrive: {pdf_path}", logger, update)
				replace_file_in_onedrive(pdf_path, annotated_pdf_path)
				await log_to_telegram(f"Successfully updated PDF in OneDrive", logger, update)
			except Exception as e:
				await log_to_telegram(f"Error updating PDF in OneDrive: {str(e)}", logger, update)
		else:
			await log_to_telegram(f"No annotations were added, OneDrive file not updated", logger, update)

	except Exception as e:
		await log_to_telegram(f"Error in PDF processing: {str(e)}", logger, update)
		logger.error(f"Error in handle_pdf_during_xml_processing: {str(e)}")
	finally:
		# Clean up temporary files
		delete_files(to_delete)

async def add_annotation_to_finding(filtered_findings, task, text_to_search):
	inst = get_rect(filtered_findings)
	highlight = filtered_findings[0]["page"].add_highlight_annot(inst)
	if task.annotation:
		content = f"timestamp: {task.recording_timestamp}\ntask_annotation: {task.annotation}\ntext_to_search: {text_to_search}"
	else:
		content = f"timestamp: {task.recording_timestamp}\ntext_to_search: {text_to_search}"

	highlight.set_info({"content": content})
	highlight.update()
	return content


def search_for_text_in_document(document, split_search_text):
	findings = []
	for index in range(len(split_search_text)):
		search_list = split_search_text[index : index + NUMBER_OF_WORDS_TO_SEARCH]
		if len(search_list) == NUMBER_OF_WORDS_TO_SEARCH:
			words_to_search = " ".join(search_list)
			for page in document:
				text_instances = page.search_for(words_to_search)
				if len(text_instances):
					findings.append({"page": page, "text_instances": text_instances})
	return findings


async def update_task_with_page_numbers(page_numbers, task):
	new_description = json.loads(task.description)
	new_description["found_pages"] = page_numbers
	await update_description(
		task.id,
		json.dumps(new_description, indent=4, sort_keys=True, ensure_ascii=False),
	)
