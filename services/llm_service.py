import numpy as np
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from quarter_lib.akeyless import get_secrets
from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)


CHUNK_SIZE = 10
groq_api_key = get_secrets(
    ["groq/api_key"]
)

chat = ChatGroq(temperature=0.5, model_name="llama-3.3-70b-versatile",
                groq_api_key=groq_api_key)

parser = JsonOutputParser()

prompt = PromptTemplate(
    template="""You are summarizing a list of personal notes. Summarize each note individually, ensuring it is concise and retains its main meaning. Provide the output as a list of unique summarized notes in the same order as the input list. Don't translate the notes and use the language provided in the notes. Don't use any special characters and keep the summary as short as possible.\n{format_instructions}\n{notes}\n""",
    input_variables=["notes"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

chain = prompt | chat | parser


def get_summary(item_list):
    # create some retry logic here
    for i in range(3):
        try:
            result =  chain.invoke({"notes": item_list})["notes"]
            if len(result) != len(item_list):
                raise Exception("Result length does not match input length")
            logger.info(f"Got result from langchain: {str(result)}")
            return result
        except Exception:
            logger.exception("Error in get_summary")

    return chain.invoke({"notes": item_list})["notes"]


def get_summaries(content_list:list):
    chunks = np.array_split(list(content_list), len(list(content_list)) // CHUNK_SIZE + 1)
    summaries = []
    for chunk in chunks:
        summaries.extend(get_summary(chunk))
    return summaries