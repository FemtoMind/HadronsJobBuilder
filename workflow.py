#Organization and addition of gauge config info
from langchain_openai import ChatOpenAI
from hadrons_config import *
from langchain.messages import (
    SystemMessage,
    HumanMessage,
    ToolCall,
    AIMessage
)

llm = ChatOpenAI(
    model="gpt-oss-120b-GGUF",
    openai_api_key="sk-local",
    openai_api_base="http://localhost:8000/v1"
)

zerot_llm = ChatOpenAI(
    model="gpt-oss-120b-GGUF",
    openai_api_key="sk-local",
    openai_api_base="http://localhost:8000/v1",
    temperature=0
)
          
#query = input("What is your question? :")
#query = "Compute the pion two-point and vector two-point functions using propagators of mass 0.01 and 0.03."
#query = "Compute the pion two-point function with DWF propagators of mass 0.01 and 0.03, and again with masses 0.02 and 0.04."

#query = """Compute the pion two-point function with DWF propagators of mass 0.01 and 0.03, and again with masses 0.02 and 0.04.
#General parameters:
#Ls=12
#M5=1.8"""

#query = """Compute the pion two-point function with DWF wall-source propagators of mass 0.01 and 0.03 and source timeslice t=0, and again with masses 0.02 and 0.04 and source timeslice t=32. Assign momentum [1,2,3,4] to the sources at timeslice t=32.
#General parameters:
#M5=1.8"""

#query = "Compute the pion two-point function"
query = "Compute the pion two-point function with mass 0.01 for both propagators and again with mass 0.02 for both"


print(query)
agent(query, zerot_llm, reload_state=True, ckpoint_file="state.json")

