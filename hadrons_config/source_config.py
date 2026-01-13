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
from .hadrons_xml import HadronsXML
import json
from .common import *

class PointSource(BaseModel):
    """A point or single-location source"""
    type: Literal["point"] = "point"
    location: Tuple[NonNegativeInt,NonNegativeInt,NonNegativeInt,NonNegativeInt] = Field(..., description="The point source 4D location")

    def setXML(self,name,xml):
        opt = xml.addModule(name,"MSource::Point")
        HadronsXML.setValue(opt, "position", spaceSeparateSeq(self.location))
        
    
class WallSource(BaseModel):
    """A wall or wall-momentum (aka just "momentum") source. A wall source requires just a timeslice, whereas a wall-momentum source needs a momentum also."""
    type: Literal["wall"] = "wall"
    timeslice: int = Field(..., description="time slice of the wall")
    momentum: Optional[Tuple[float,float,float,float]] = Field(
        None, description="Optional four-momentum"
    )

    def setXML(self,name,xml):
        opt = xml.addModule(name,"MSource::Wall")
        HadronsXML.setValues(opt, [ ("tW",self.timeslice), ("mom", "0. 0. 0. 0." if self.momentum == None else spaceSeparateSeq(self.momentum) ) ])


    
class SourceConfig(BaseModel):
    name : str = Field(..., description="The name/tag for the source")
    source: Union[PointSource, WallSource] = Field(
        ..., description="Information about the source. Each item must have a 'type' field. Valid values are: 'point', 'wall'  "  #Note, without specifying the valid values here, the agent accepted invalid options
    )
    observables: List[str] = Field(...,description="The observable instances to which this source will be associated")
    
    def setXML(self,xml):
        self.source.setXML(self.name,xml)
    

class SourcesConfig(BaseModel):
    sources: List[SourceConfig] = Field(...,description="The list of source instances")



def identifySources(model, state, user_interactions: list[BaseMessage]) -> SourcesConfig:
    """
    Parse the list of messages to identify a list of propagator sources and their associated parameters
    """
    
    sys = """
You are an assistant responsible for identifying all lattice QCD propagator sources required to compute the propagators required for the calculation, based solely on user input.

A source instance has a source type (e.g. point, wall) along with a set of parameters that depend on the source type. Each propagator requires a source, but can share the same source instance. Create a separate entry for each unique collection of parameters, for example if the user specified propagators with point sources at [0,0,0,0] and [12,24,12,24], create two separate source instances with different source locations.
    
For each required propagator:
1. Identify the appropriate schema for the 'source' field based on the requires source type. If the user does not specify a source type you must ask the user. Never guess a source type.
2. Fill in all parameters of the source field as specified by the user. If a parameter value is unknown you must ask the user; never guess parameters.
3. Assign a unique tag/name to the instance. Never use the same tag for different instances. The tag should include the action name and enough of the parameter values to uniquely distinguish it among the other source instances, prefering shorter tags if possible.
4. Fill the 'observables' field with a list of the observable instance names/tags that this source will be used for    

Source instance rules:    
- Create a separate entry for each action instance, even if the action appears multiple times with different parameters.
- Your list must include every source instance explicitly mentioned, and only those. Do not invent instances. do not combine instances unless the user explicitly describes them as the same.

User Query rules:
- Use the getUserInput tool
- If the user responds to a query with an invalid response, repeat the query until a valid response is provided. Never accept an invalid response.
- Instead of answering your question, the user might respond to your query with a question. If this occurs, answer the user's question using provideInformationToUser tool and ensure the user is satisfied with a follow-up call to getUserInput. Once satisfied, repeat the original question.
    
Your output must be in JSON format and adhere to the following schema:    
""" + json.dumps(SourcesConfig.model_json_schema())  ##appears necessary to also include the schema in the prompt else it hallucinates valid actions and does not validate
    
    agent = create_agent(model=model, tools=[getUserInput,provideInformationToUser], system_prompt=sys, response_format=ToolStrategy(SourcesConfig))
    
    accepted = False
    obj = None
    while(accepted == False):    
        resp = agent.invoke({ "messages": user_interactions })
        #print(resp)
        obj = resp["structured_response"]        

        #Auto validation
        valid = True
        invalid_why = "Your previous response was invalid for the following reason(s):"
        names = []
        for r in obj.sources:
            if r.name in names:
                invalid_why += f"\n-Source name '{r.name}' is not unique"
                valid = False
            names.append(r.name)
                                
        if not valid:
            user_interactions.append(HumanMessage(invalid_why))
            continue       
        
        #Human validation
        Print("Obtained", len(obj.sources), "sources")
        for r in obj.sources:
            Print(r)

        accepted = queryYesNo("Is this correct? [y/n]: ")
        if(accepted == False):
            reason = Input("Explain what is wrong: ")
            user_interactions.append(HumanMessage(f"Your previous response was not accepted for the following reason: {reason}"))            
    return obj
