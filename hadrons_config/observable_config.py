from langchain_core.messages import BaseMessage
from langchain.messages import (
    SystemMessage,
    HumanMessage,
    ToolCall,
    AIMessage
)

from pydantic import BaseModel, Field, ConfigDict, NonNegativeInt, TypeAdapter
from typing import Literal, Union, List, Optional, Tuple
from langgraph.func import task
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy
from .common import *

class Pion2ptConfig(BaseModel):
   """An instance of the pion two-point function calculation."""
   type: Literal["pion2pt"] = "pion2pt"
   propagators : tuple[str,str] = Field(..., description="The tags of the propagators used to compute the observable")

class Vector2ptConfig(BaseModel):
   """An instance of the vector two-point function calculation."""
   type: Literal["vector2pt"] = "vector2pt"
   propagators : tuple[str,str] = Field(..., description="The tags of the propagators used to compute the observable")
  
class ObservableConfig(BaseModel):
   """An instance of an observable."""
   obs: Union[Pion2ptConfig,Vector2ptConfig] = Field(...,description="The observation instance and configuration.")
    
class ObservablesConfig(BaseModel):
    observable_configs: List[ObservableConfig] = Field(...,description="The list of observable instances and their configurations")


@task
def configureObservables(model, user_interactions: list[BaseMessage]) -> ObservablesConfig:
    sys = """
    Reasoning: high

    You are an assistant responsible for building a list of lattice QCD observable instances and their associated parameters based on the conversation history.

    In previous stages of the workflow, agents identified a list of observables that will be computed alongside some associated information. For each and every observable in this list you must determine the associated propagators and other parameters.

    Your workflow:

    For every ObservableInfo in the list contained within the message history:
    1. Parse the user information and background knowledge for the observable
    2. Identify the propagators required to compute this observable and note their names/tags
    3. Add a new ObservableConfig with matchin 'type' enum and populate the associated parameters

    Your list must include every observable in the list and only those. Do not invent observables, do not combine observables, and do not add details that are not explicitly provided by the user.
    Do not invent or infer any information not explicitly obtained from the message history.
"""

    accepted = False
    obj = None
    while(accepted == False):
        obj = callModelWithStructuredOutput(model, sys, user_interactions, ObservablesConfig, True)

        print("Obtained", len(obj.observable_configs), " observable configurations")
        for r in obj.observable_configs:
            print(r)
            
        accepted = queryYesNo("Is this correct? [y/n]: ")
        if(accepted == False):
            reason = input("Explain what is wrong: ")
            user_interactions.append(HumanMessage(f"Your previous response was not accepted for the following reason: {reason}"))            
    return obj
