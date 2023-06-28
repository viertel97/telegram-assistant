import json
import os
import re

import fitz
import pandas as pd
from loguru import logger
from telegram import Update

from services.todoist_service import get_items_by_todoist_project, run_todoist_sync_commands, update_description

FINDING_THRESHOLD = 0.75

logger.add(
    os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/logs/" + os.path.basename(__file__) + ".log"),
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    backtrace=True,
    diagnose=True,
)

LANGUAGE = "de"
NUMBER_OF_WORDS_TO_SEARCH = 4


def filter_content(task):
    return task | json.loads(task['description'])


def get_rect(findings):
    x0y0 = findings[0]['text_instances'][0][0]
    x0y1 = findings[0]['text_instances'][0][1]
    x1y0 = findings[0]['text_instances'][0][2]
    x1y1 = findings[0]['text_instances'][0][3]
    return fitz.Rect(x0y0, x0y1, x1y0, x1y1)


def get_filtered_findings(findings):
    page_numbers = [page['page'].number for page in findings]
    proportions = pd.Series(page_numbers).value_counts(normalize=True)
    if proportions.head(1).values[0] > FINDING_THRESHOLD:
        return [page for page in findings if page['page'].number == proportions.head(1).index[0]], page_numbers
    return None, page_numbers


async def handle_pdf(file_path, file_name, update: Update):
    tasks = get_items_by_todoist_project("2281154095")
    tasks = [filter_content(task.__dict__) for task in tasks]
    df = pd.DataFrame(tasks)
    grouped_df = df.groupby("title")
    splitted_caption = update.message.caption.split(" § ")
    selected_book_from_todoist, selected_language = splitted_caption[0], splitted_caption[1]
    if selected_book_from_todoist in grouped_df.groups:
        group = grouped_df.get_group(selected_book_from_todoist)
        document = fitz.open(file_path)
        not_found_counter = 0
        try:
            file_version = int(re.search(r"V[0-9]{1,2}", file_name).group(0)[1:])
        except AttributeError:
            file_version = 1
        command_list = []
        for _, task in group.iterrows():
            text_to_search = task["recognized_text_" + selected_language]
            logger.info("text to search: {}".format(text_to_search))
            split_search_text = text_to_search.split(" ")
            findings = await search_for_text_in_document(document, split_search_text)
            logger.info(f"found {len(findings)} entries for '{text_to_search}'")
            if len(findings):
                filtered_findings, page_numbers = get_filtered_findings(findings)
                if filtered_findings:
                    try:
                        await add_annotation_to_finding(filtered_findings, task, text_to_search)
                        command_list.append({"type": "item_close", "args": {"id": task.id}})

                    except ValueError as e:
                        not_found_counter += 1
                        logger.error(e)
                        await update_task_with_page_numbers(page_numbers, task)
                        await update.message.reply_text("Error while highlighting text '{}' on page {}.".format(
                            text_to_search, page_numbers[0]))
                else:

                    not_found_counter += 1
                    await update_task_with_page_numbers(page_numbers, task)
                    await update.message.reply_text(
                        "The text '{}' was found on different pages [{}] and can't be highlighted".format(
                            text_to_search,
                            str(page_numbers))
                        , disable_notification=True)
                    logger.info("found entries are not in the same page")
            else:
                logger.info("nothing found")
        new_file_path = file_path[:-4].replace("_V" + str(file_version), "")
        new_file_path = os.path.join(new_file_path + "_V" + str(file_version + 1) + ".pdf")
        document.save(new_file_path)
        await update.message.reply_document(document=open(new_file_path, "rb"),
                                            caption="'{}' out of possible '{}' could not have been added - therefore '{}' annotations has been added sucecessfully to the PDF '{}'.".format(
                                                not_found_counter, group.shape[0], group.shape[0] - not_found_counter,
                                                file_name))
        os.remove(file_path)
        os.remove(new_file_path)
        response = run_todoist_sync_commands(command_list)
    else:
        logger.error("no book for the caption '{}' found".format(selected_book_from_todoist))
        await update.message.reply_text("no book for the caption '{}' found".format(selected_book_from_todoist))


async def add_annotation_to_finding(filtered_findings, task, text_to_search):
    inst = get_rect(filtered_findings)
    highlight = filtered_findings[0]['page'].add_highlight_annot(inst)
    if task.annotation:
        content = "task_annotation: " + task.annotation + "\n" + "text_to_search: " + text_to_search
    else:
        content = "text_to_search: " + text_to_search
    highlight.set_info({"content": content})
    highlight.update()


async def search_for_text_in_document(document, split_search_text):
    findings = []
    for index in range(len(split_search_text)):
        search_list = split_search_text[index: index + NUMBER_OF_WORDS_TO_SEARCH]
        if len(search_list) == NUMBER_OF_WORDS_TO_SEARCH:
            words_to_search = " ".join(search_list)
            for page in document:
                text_instances = page.search_for(words_to_search)
                if len(text_instances):
                    findings.append(
                        {"page": page, "text_instances": text_instances})
    return findings


async def update_task_with_page_numbers(page_numbers, task):
    new_description = json.loads(task.description)
    new_description['found_pages'] = page_numbers
    await update_description(task.id, json.dumps(new_description, indent=4, sort_keys=True))
