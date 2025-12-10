from langchain_core.messages import BaseMessage
from langchain.messages import (
    SystemMessage,
    HumanMessage,
    ToolCall,
    AIMessage
)
import json
from pydantic import BaseModel, Field, ConfigDict, NonNegativeInt, TypeAdapter
from typing import Literal, Union, List, Optional, Tuple
from langgraph.func import task
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy
from langchain.agents import create_agent
from .common import *
from .hadrons_xml import HadronsXML

class RBPrecCGsolver(BaseModel):
    """red-black preconditioned conjugate gradient (CG) solver"""
    type: Literal["RBPrecCG"] = "RBPrecCG"
    residual: float = Field(...,description="the solver tolerance, residual or stopping condition. Typical values are in the range 1e-6 to 1e-9")
    maxIteration: NonNegativeInt = Field(10000,description="maximum number of solver iterations. Default=10000. DEFAULTABLE.")

    def setXML(self,name,action,xml):
        opt = xml.addModule(name,"MSolver::RBPrecCG")
        HadronsXML.setValues(opt, [ ("action",action), ("maxIteration", self.maxIteration), ("residual", self.residual), ("guesser", "") ])

    
class SolverConfig(BaseModel):
    name : str = Field(..., description="The name/tag for the solver instance")
    solver_args: Union[RBPrecCGsolver] = Field(..., description="Parameters of the solver. Each item must have a 'type' field. Valid values are: RBPrecCG")
    action: str = Field(..., description="The name/tag of the action instance to use with the solver.")

    def setXML(self,xml):
        self.solver_args.setXML(self.name,self.action,xml)
    
class SolversConfig(BaseModel):
    solvers: List[SolverConfig] = Field(...,description="The list of solver instances")

@task
def identifySolvers(model, user_interactions: list[BaseMessage]) -> SolversConfig:
    """
    Parse the list of messages to identify a list of solver instances and their associated parameters
    """
    
    sys = """
You are an assistant responsible for identifying the solvers required for computing the lattice QCD propagators for the calculation.

A solver instance has a set of parameters such as stopping conditions and the maximum number of iterations. The instance also has an 'action' field, that must be set to the name of one of the action instances identified previously. Each action instance must have one or more solver instances associated with it.
    
Create a separate entry for each unique collection of parameters, for example if the user specified the RBPrecCG solver type and there are action instances with names "action_1" and "action_2", create two separate solver instances with different values for the 'action' parameter.
    
- For each required solver:
1. Identify the name of the associated action instance and use it to fill the 'action' parameter.
2. Identify the appropriate schema for the 'solver_args' field based on the requires solver type. If the user does not specify a solver type you must ask the user unless there is only one option. Never guess a solver type if there are more than one options.
3. Fill in all parameters of the solver_args field as specified by the user. If a parameter value is unknown you must ask the user; never guess parameters unless they are specifically described with the word DEFAULTABLE, which indicates that the default value can be chosen.
4. Assign a unique tag/name to the solver instance. Never use the same tag for different instances. The tag should include the action name and enough of the parameter values to uniquely distinguish it among the other source instances, prefering shorter tags if possible. 

- Ensure there is at least one solver instance per action instance.
    
Solver instance rules:    
- Create a separate entry for each solver instance, even if the solver appears multiple times with different parameters.
- Your list must include every solver instance explicitly mentioned, and only those. Do not invent instances. do not combine instances unless the user explicitly describes them as the same.

User Query rules:
- Use the getUserInput tool
- If the user responds to a query with an invalid response, repeat the query until a valid response is provided. Never accept an invalid response.
- Instead of answering your question, the user might respond to your query with a question. If this occurs, answer the user's question using provideInformationToUser tool and ensure the user is satisfied with a follow-up call to getUserInput. Once satisfied, repeat the original question.
    
Your output must be in JSON format and adhere to the following schema:    
""" + json.dumps(SolversConfig.model_json_schema())
    
    agent = create_agent(model=model, tools=[getUserInput,provideInformationToUser], system_prompt=sys, response_format=ToolStrategy(SolversConfig))
    
    accepted = False
    obj = None
    while(accepted == False):    
        resp = agent.invoke({ "messages": user_interactions })
        print(resp)
        obj = resp["structured_response"]        
        
        print("Obtained", len(obj.solvers), "solvers")
        for r in obj.solvers:
            print(r)

        accepted = queryYesNo("Is this correct? [y/n]: ")
        if(accepted == False):
            reason = input("Explain what is wrong: ")
            user_interactions.append(HumanMessage(f"Your previous response was not accepted for the following reason: {reason}"))            
    return obj
