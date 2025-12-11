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
from .hadrons_xml import HadronsXML

def mesonModuleXML(name, xml, gammas_snk_src: str, q1 : str, q2 : str):
    #NB: gamma5-hermiticity used on q2
    opt = xml.addModule(name, "MContraction::Meson")

    HadronsXML.setValues(opt, [ ("q1", q1), ("q2", q2), ("gammas", gammas_snk_src), ("sink", "point_sink_zerop"), ("output",f"{name}.out") ])

def validateProps(prop_names, state):
    for p in prop_names:
        if not state.isValidPropagator(p):
            return (False, f"-Propagator instance {p} does not exist")
    return (True,"")

    
class Pion2ptConfig(BaseModel):
    """An instance of the pion two-point function calculation."""
    type: Literal["pion2pt"] = "pion2pt"
    propagators : tuple[str,str] = Field(..., description="The tags of the propagators used to compute the observable")

    def setXML(self, name, xml):
        mesonModuleXML(name, xml, "(Gamma5 Gamma5)", self.propagators[0], self.propagators[1])
       
    def validate(self, state):
        return validateProps(self.propagators,state)
       
   
class Vector2ptConfig(BaseModel):
    """An instance of the vector two-point function calculation."""
    type: Literal["vector2pt"] = "vector2pt"
    propagators : tuple[str,str] = Field(..., description="The tags of the propagators used to compute the observable")

    def setXML(self, name, xml):
        gammas = ""
        for gsnk in ("GammaX","GammaY","GammaZ"):
            for gsrc in ("GammaX","GammaY","GammaZ"):
                gammas = gammas + f"({gsnk} {gsrc})"
       
        mesonModuleXML(name, xml, gammas, self.propagators[0], self.propagators[1])

    def validate(self, state):
        return validateProps(self.propagators, state)
   
class ObservableConfig(BaseModel):
    """An instance of an observable."""
    name: str = Field(..., description="The name/tag of the observable instance")        
    obs: Union[Pion2ptConfig,Vector2ptConfig] = Field(...,description="The observation instance and configuration.")

    def setXML(self, xml):
        self.obs.setXML(self.name, xml)

    def validate(self, state):
        return self.obs.validate(state)
       
class ObservablesConfig(BaseModel):
    observable_configs: List[ObservableConfig] = Field(...,description="The list of observable instances and their configurations")


@task
def configureObservables(model, state, user_interactions: list[BaseMessage]) -> ObservablesConfig:
    sys = """
    Reasoning: high

    You are an assistant responsible for building a list of lattice QCD observable instances and their associated parameters based on the conversation history.

    In previous stages of the workflow, agents identified a list of observables that will be computed alongside some associated information. For each and every observable in this list you must determine the associated propagators and other parameters.

    Your workflow:

    For every ObservableInfo in the list contained within the message history:
    1. Parse the user information and background knowledge for the observable
    2. Identify the propagators required to compute this observable and note their name field. These names and no other must be used to fill the list of propagators. Use only the names of propagators, not of other types of instance (e.g. sources, solvers, actions)
    3. Assign a unique tag/name to the observable instance. Never use the same tag for different instances.
    4. Add a new ObservableConfig with matching 'type' enum and populate the associated parameters. 
    
    Your list must include every observable in the list and only those. Do not invent observables, do not combine observables, and do not add details that are not explicitly provided by the user.
    Do not invent or infer any information not explicitly obtained from the message history.
    Do not invent names for propagators, use only those assigned to existing propagators in your message history.
"""

    accepted = False
    obj = None
    while(accepted == False):
        obj = callModelWithStructuredOutput(model, sys, user_interactions, ObservablesConfig, True)

        #Auto validation
        valid = True
        invalid_why = "Your previous response was invalid for the following reason(s):"
        names = []
        for r in obj.observable_configs:
            val, rsn = r.validate(state)
            if not val:
                invalid_why += "\n" + rsn
                valid = False
            if r.name in names:
                invalid_why += f"\n-Propagator name '{r.name}' is not unique"
                valid = False
            names.append(r.name)
                                
        if not valid:
            user_interactions.append(HumanMessage(invalid_why))
            continue

        
        #Human validation
        print("Obtained", len(obj.observable_configs), " observable configurations")
        for r in obj.observable_configs:
            print(r)
            
        accepted = queryYesNo("Is this correct? [y/n]: ")
        if(accepted == False):
            reason = input("Explain what is wrong: ")
            user_interactions.append(HumanMessage(f"Your previous response was not accepted for the following reason: {reason}"))            
    return obj
