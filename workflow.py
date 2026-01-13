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
#    seed=1234   doesn't work
          
query = input("Describe the observables you wish to compute: ")
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
#query = "Compute the pion two-point function with mass 0.01 for both propagators and again with mass 0.02 for both"
#query = "Compute the pion two-point and vector two-point functions using propagators of mass 0.01 and 0.03."

#query = """Compute the pion two-point and vector two-point functions. In both cases use a propagator of mass 0.01 and another of mass 0.03.
#Other parameters:
#Use DWF quarks with M5=1.8 and Ls=12
#Use the RBPrecCG solver with residual 1e-8 and default max iterations
#Use the unit gauge
#"""

print(query)
agent(query, zerot_llm, reload_state=False)

