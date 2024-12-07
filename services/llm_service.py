from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from quarter_lib.akeyless import get_secrets

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


def get_summary(df_items):
    return chain.invoke({"notes": list(df_items.content)})["notes"]