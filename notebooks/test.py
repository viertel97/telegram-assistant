# %%
import os

from bs4 import BeautifulSoup
from loguru import logger


# %%
def read_markdown():
    with open("Output.txt", "r", encoding="utf-8") as f:
        text = f.read()
    return BeautifulSoup(text, "html.parser")


# %%
soup = read_markdown()


# %%
def get_tasks(soup):
    for child in soup.find_all("h1"):
        if child.text == "Annotations":
            start_element = child
    if not start_element:
        return "No annotations found in file"
    else:
        tasks = []
        for child in start_element.next_siblings:
            if child != "\n" and child.name == "p":
                if (
                    child.next_sibling is not None
                    and child.next_sibling.name == "blockquote"
                    and child.next_sibling.next_sibling.next_silbling.name
                    == "blockquote"
                ):
                    tasks.append(paragraph_to_task(child, child.next_sibling.text))
                else:
                    tasks.append(paragraph_to_task(child))
        return tasks


def paragraph_to_task(paragraph, comment=None):
    text = ""
    for child in paragraph.contents:
        if child.name != "a":
            text += child.text
        else:
            text += "[{text}]({link})".format(text=child.text, link=child["href"])
    if comment:
        return (text, comment)
    else:
        return text


tasks = get_tasks(soup)
