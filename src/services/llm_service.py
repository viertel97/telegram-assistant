import numpy as np
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)


CHUNK_SIZE = 10
groq_api_key = get_secrets(["groq/api_key"])

chat = ChatGroq(temperature=0.5, model_name="llama-3.3-70b-versatile", groq_api_key=groq_api_key)

parser = JsonOutputParser()

prompt = PromptTemplate(
	template="""
Summarize a list of note titles, retaining the main meaning of each title. Summarize each note individually, ensuring the output is concise. If a title is too short or represents a raw thought process, return it as-is. The output must be a list of unique summarized titles in the same order as the input list.
Always ensure the number of entries in the output matches the input list - even if entries are duplicates. Avoid using special characters, and do not translate or alter the language of the titles.
\n{format_instructions}\n{notes}\n""",
	input_variables=["notes"],
	partial_variables={"format_instructions": parser.get_format_instructions()},
)

chain = prompt | chat | parser


def get_summary(item_list):
	# create some retry logic here
	for i in range(3):
		try:
			result = chain.invoke({"notes": item_list})
			if isinstance(result, dict):
				keys = list(result.keys())
				result = result.get(keys[0])
			if len(result) != len(item_list):
				raise Exception("Result length does not match input length")
			logger.info(f"Got result from langchain: {result!s}")
			return result
		except Exception:
			logger.exception("Error in get_summary")
			raise Exception("Error in get_summary")


def get_summaries(content_list: list):
	chunks = np.array_split(list(content_list), len(list(content_list)) // CHUNK_SIZE + 1)
	summaries = []
	for chunk in chunks:
		summaries.extend(get_summary(chunk))
	return summaries
