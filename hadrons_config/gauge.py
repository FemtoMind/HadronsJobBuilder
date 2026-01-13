from langchain_core.messages import BaseMessage
from langchain.messages import (
    SystemMessage,
    HumanMessage,
    ToolCall,
    AIMessage
)

from pydantic import BaseModel, Field, ConfigDict, NonNegativeInt, TypeAdapter
from typing import Literal, Union, List, Optional, Tuple
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langgraph.store.memory import InMemoryStore

import json
from .common import *
from .hadrons_xml import HadronsXML

class LoadGauge(BaseModel):
    """Load NERSC-format gauge configurations. If the user provides a range, infer from it the start, step and end."""
    type: Literal["gauge-load"] = "gauge-load"
    stub : str = Field(...,description="The path stub of the configurations. A period followed by the configuration index will be appended during the run. If the user provides a complete path including an index (or variable_, remove the period and index")
    start : int = Field(...,description="The index of the first configuration")
    step : int = Field(...,description="The increment between successive configurations")
    end : int = Field(...,description="The index of the last configuration")

    def setXML(self,xml):
        opt = xml.addModule("gauge","MIO::LoadNersc")
        HadronsXML.setValue(opt, "file", self.stub)
        xml.setTrajCounter(self.start, self.end, self.step)
                            

    
class UnitGauge(BaseModel):
    """Use a unit gauge configuration"""
    type: Literal["gauge-unit"] = "gauge-unit"

    def setXML(self,xml):
        xml.addModule("gauge","MGauge::Unit")
        xml.setTrajCounter(0,1,1)
        
class RandomGauge(BaseModel):
    """Use a random gauge configuration"""
    type: Literal["gauge-random"] = "gauge-random"
    def setXML(self,xml):
        xml.addModule("gauge","MGauge::Random")
        xml.setTrajCounter(0,1,1)
    
class GaugeFieldConfig(BaseModel):
    config: Union[LoadGauge,UnitGauge,RandomGauge] = Field(
        ..., description="Information about the gauge configuration(s) that will be computed upon."
    )
    def setXML(self,xml):
        self.config.setXML(xml)

#This seems to be another one that confuses ToolStrategy, giving incorrect structured output
@tool
def setUnitGauge(runtime: ToolRuntime) -> None:
    """Use a unit gauge configuration"""
    runtime.store.put(("ns",), "gauge", UnitGauge())
@tool
def setRandomGauge(runtime: ToolRuntime) -> None:
    """Use a random gauge configuration"""
    runtime.store.put(("ns",), "gauge", RandomGauge())

@tool
def setLoadGauge(stub : str, start: int, step: int, end: int, runtime : ToolRuntime) -> None:
    """Load NERSC-format gauge configurations.
    Args:
        stub : The path stub of the configurations. A period followed by the configuration index will be appended during the run. If the user provides a complete path including an index (or variable_, remove the period and index)
        start : The index of the first configuration
        step : The increment between successive configurations
        end : The index of the last configuration
    Instructions:
        If the user provides a range, infer from it the start, step and end.
    """
    runtime.store.put(("ns",), "gauge", LoadGauge(stub=stub, start=start, step=step, end=end))

    

def identifyGaugeConfigs(model, user_interactions: list[BaseMessage]) -> GaugeFieldConfig:
    sys = """
You are an assistant responsible for identifying the lattice QCD propagator gauge configuration(s) to use for the calculation, based solely on user input.

Your workflow:
1. Identify the appropriate tool for the gauge configuration specification based on user input. If the user does not specify what configuration(s) to use you must ask the user. Never guess a gauge type.
2. Call the tool with its required parameters. If a parameter value is unknown you must ask the user; never guess parameters.
       
User Query rules:
- Use the getUserInput tool
- If the user responds to a query with an invalid response, repeat the query until a valid response is provided. Never accept an invalid response.
- Instead of answering your question, the user might respond to your query with a question. If this occurs, answer the user's question using provideInformationToUser tool and ensure the user is satisfied with a follow-up call to getUserInput. Once satisfied, repeat the original question.
"""
    
#Your output must be in JSON format and adhere to the following schema:    
#""" + json.dumps(GaugeFieldConfig.model_json_schema())
# Your workflow:
# 1. Identify the appropriate schema for the 'config' field based on user input. If the user does not specify what configuration(s) to use you must ask the user. Never guess a gauge type.
# 2. Fill in all parameters associated with the gauge field instance. If a parameter value is unknown you must ask the user; never guess parameters.

    store = InMemoryStore()

    agent = create_agent(model=model, tools=[getUserInput,provideInformationToUser,setUnitGauge,setRandomGauge,setLoadGauge], system_prompt=sys, store=store) #, response_format=ToolStrategy(GaugeFieldConfig))
    
    accepted = False
    obj = None
    while(accepted == False):    
        resp = agent.invoke({ "messages": user_interactions },     {"configurable": {"thread_id": "1"}})
        config = store.get( ("ns",), "gauge").value
        obj = GaugeFieldConfig(config=config)
        
        Print("Obtained gauge field parameters:", obj.config)

        accepted = queryYesNo("Is this correct? [y/n]: ")
        if(accepted == False):
            reason = Input("Explain what is wrong: ")
            user_interactions.append(HumanMessage(f"Your previous response was not accepted for the following reason: {reason}"))            
    return obj
