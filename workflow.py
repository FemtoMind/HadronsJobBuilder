from langchain_openai import ChatOpenAI
from hadrons_config import *

local_llm = ChatOpenAI(
    model="gpt-oss-120b-GGUF",
    openai_api_key="sk-local",
    openai_api_base="http://localhost:8000/v1",
    temperature=0
)

amsc_llm_0t = ChatOpenAI(
    model="gpt-oss-120b",
    base_url="https://api.i2-core.american-science-cloud.org/",
    temperature=0
)

llm = amsc_llm_0t

query = input("Describe the observables you wish to compute: ")
print(query)
agent(query, llm, reload_state=True)

