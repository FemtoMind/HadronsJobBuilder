from typing import Tuple
from femtomeas.meas_config_agent.state import State
from .manager import JobManager, TransferToAction, TransferFromAction, HadronsComputeAction, HadronsJobSpec
from . import globals
from .logging import wfmanLog


from langchain_core.messages import BaseMessage
from langchain.messages import (
    SystemMessage,
    HumanMessage,
    ToolCall,
    AIMessage
)

from pydantic import BaseModel, Field, ConfigDict, NonNegativeInt, TypeAdapter, PositiveFloat, PositiveInt, create_model
from typing import Literal, Union, List, Optional, Tuple, Any
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy
from langchain.agents import create_agent
from langchain.agents.middleware import before_model, after_model, AgentState
import json
from femtomeas.meas_config_agent.common import getUserInput, provideInformationToUser, queryYesNo, prettyPrintPydantic, Print as AgentPrint, Input as AgentInput
from femtomeas.workflow_manager.api_general import getKnownMachines, getUserAccountProjects, getMachineQueues
from langchain.tools import tool
from .hadrons import defaultRankGeom
from langgraph.checkpoint.memory import MemorySaver
from langgraph.runtime import Runtime


from typing import Callable
from langchain.agents.middleware import (
    wrap_model_call,
    ModelRequest,
    ModelResponse,
    AgentState,
    ExtendedModelResponse
)
from langgraph.types import Command
from typing_extensions import NotRequired


def enqueueStandardHadronsWorkflow(state : State, jman : JobManager,
                            mpi : Tuple[int,int,int,int],
                            machine : str, group_name : str,
                            account: str, queue : str, time : str,
                            stage_out: Tuple[str,str] | None = None
                            ):
    """
    stage_out : If not None, provide a tuple containing the destination Globus endpoint and a path. Files will be placed in subdirectories of that path labeled by the job index
    """
    
    configs, source_uuid = state.gauge.getJobConfigurationsAndSource()
    grid = state.gauge.getGrid()
    
    if machine not in globals.remote_workdir:
        raise Exception(f"Unknown machine {machine}")
    
    job_dir = globals.remote_workdir[machine] + f"/{group_name}/<JOBID>"
    cfg_staging_dir = globals.remote_workdir[machine] + f"/{group_name}/configurations"

    wfmanLog("enqueueStandardHadronsWorkflow is queueing",len(configs),"configurations:", configs)
    for i in range(len(configs)):
        workflow = []

        #If the configs are remote they will need to staged in
        override_cfgpath = None
        if source_uuid != None and configs[i] != None:
            action = TransferToAction(source_endpoint=source_uuid, source_path=configs[i], machine=machine, dest_path=cfg_staging_dir)
            workflow.append(action)
            override_cfgpath = cfg_staging_dir

        xml = state.toHadronsXMLsingleConf(i, override_path = override_cfgpath)
        spec = HadronsJobSpec(job_rundir=job_dir, xml=xml, grid=grid)

        workflow.append(
            HadronsComputeAction(machine=machine, account=account, queue=queue, time=time, spec=spec, mpi=mpi)
            )

        if stage_out:
            workflow.append(TransferFromAction(machine=machine, source_path=job_dir, dest_endpoint=stage_out[0], dest_path=stage_out[1])) 
            
            
        with jman as jd:
            jd.enqueueJob(workflow, group_name)

@tool
def agentGetKnownMachines() -> List[str]:
    """
    Get a list of valid machine names.

    Note that this list of known machines is not exhaustive; rather FemtoMeas has an inbuilt mapping of known machines to their IRI API addresses. Functionality is not yet available to extend this.

    Return:
    A list of known machines
    """
    return getKnownMachines()

@tool
def agentGetUserAccounts(machine : str)-> List[str]:
    """
    Get a list of accounts on a particular machine

    Args:
    machine: The name of the machine

    Return:
    A list of user accounts
    
    """  
    return getUserAccountProjects(machine)

@tool
def agentGetMachineQueues(machine: str)->List[ Tuple[str,str] ]:
    """
    Provide a list of queues and associated information for a given machine

    Args:
    machine: The name of the machine
    
    Return: a list of string tuples, with the first tuple entry being the queue name and the second relevant information about the queue
    """
    return getMachineQueues(machine)

state_ = None

@tool
def getLatticeSize()->Tuple[int,int,int,int]:
    """
    Get the lattice size of the job as a tuple of four integers (Lx,Ly,Lz,Lt)
    """
    return state_.gauge.getGrid()

@tool
def getDefaultRankGeometry(ranks : int)->Tuple[int,int,int,int]:
    """
    Compute a suitable MPI decomposition given a specific total number of MPI ranks.

    Args:
       ranks: The total number of MPI ranks to use
    """
    geom, _ = defaultRankGeom(ranks, state_.gauge.getGrid())
    return geom
  

class JobSubmissionParameters(BaseModel):
    """Parameters for Job submission"""
    machine: str =  Field(..., description="The name of the machine on which the jobs will be executed")
    account: str = Field(..., description="The user account on the machine")
    queue: str = Field(..., description="The queue on the machine")
    duration: int = Field(...,description="The job time in seconds")
    rank_geom: Tuple[int,int,int,int] = Field(..., description="The MPI rank decomposition of the lattice. The four integers indicate the number of ranks in the x,y,z,t directions, respectively. The total number of ranks is the product of these four numbers.")
    job_group: str = Field(...,description="A name to assign this collection of jobs.")
    copy_out: Tuple[str,str] | None = Field(...,description="A tuple containing 1) the Globus endpoint UUID and 2) the base path, for copying out results to a remote machine. Use None if and only if the user specifies that they don't want to copy out the results.")

class ParameterCheck(BaseModel):
    missing_parameters: List[str] =  Field(..., description="The list of parameters for which the users has not specified a value.")
    


@after_model
def log_response(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """
    Hook to debug model state after calls (sadly does not trigger before processing structured output)
    """
    print(f"Model state: {state}")
    return None

def hadronsSubmissionAgent(state : State, jman : JobManager, model):
    AgentPrint("""
---        
## JOB SUBMISSION PARAMETERS
---
        """)       
    
    
    global state_
    state_ = state

    sys = """
    You are a conversational agent responsible for gathering information from the user for submitting a collection of batch jobs to American Science Cloud (AmSC) compute resources via the IRI API (a REST API for controlling the compute resources)

    To output text to the user, output a message containing the text for the user (questions, answers). The user's response will be contained in the next message. Your output *must* include either
    1) ONE question
    2) ONE answer to the user's previous question AND ONE further question
    NEVER output text not intended for the user such as notes-to-self. See the output rules below.
    
    The overall goal of your conversation is to aid the user in choosing values for each for the fields in the schema JobSubmissionParameters (provided below).
  
    To formulate the response, you are free to call appropriate tools to obtain extra information to help the user.

    To identify if the user has chosen a value, confirm that the user's response is a statement describing a valid value for the parameter.
    
    Obtain the values for the parameters in the order they appear in JobSubmissionParameters
    
    If the user asks a question, you must answer it before asking any further questions

    Once the user has specified all parameters, respond with "<DONE>" and nothing else.

    DO NOT PERFORM ANY PLANNING STEPS
    
    You must adhere to the following rules:      
    -----------------------------------------
    Output rules
    -----------------------------------------
    - Never ask more than one question at a time. Always wait for the user to respond before asking your next question.
    - In your response to the user, *never* include any reasoning, chain-of-thought or notes-to-self. Only ever include a single question or an answer followed by a question. For example, never output "We need to wait for user response."
    - If you do decide to include reasoning in your output despite these explicit instructions *not to*, you may receive an error message. Do not apologize, simply generate the correct output
    - If the user has not responsed to your question, do not think ahead to the next question. Wait for the user to respond.
    
    -------------------------------------------
    General Parameter Rules:
    -------------------------------------------
    - **Never** guess a parameter. The values should always be obtained from the user. Never record a parameter value unless it has been explicitly provided by the user. Follow the User Query rules below for questions to the user.

    -------------------------------------------
    Tool Rules:    
    -------------------------------------------
    - If a tool provides a list of valid responses, only accept values from among that list as valid choices by the user. If you list the values, ensure you only list those returned by the tool; never make up entries.
    - For getDefaultRankGeometry, the number of MPI ranks input to this tool must be that explicitly specified by the user. Never assume or guess a number of ranks
    
    -------------------------------------------
    User Query rules:
    -------------------------------------------
    - Never ask if the user wants to specify a parameter; assume that the user wants to specify all parameters
    - Be brief and to the point with your question, and do not ask for more than one value in a single question.
    - If you ask a question where the user is asked to choose between a set of known options, first obtain the list of options (calling any appropriate tools) then list those options alongside the question in your response. If there are more than 6 choices, list only the first 6 and indicate that there are more options.
    - If the user responds to a query with an invalid response, your response should explain that the choice is invalid and ask the question again. Never ask a question about the next field without a valid response to the current field.
    - Instead of answering your question about a parameter, the user might respond to your query with a question of their own. If this occurs:
         - On the first line of your response, answer the user's question
         - On a separate line repeat the original question about the parameter but include a statement indicating that they can ask follow-up questions
    
    -------------------------------------------
    Additional rules for specific parameters:   
    -------------------------------------------

    - rank_geom:
        - First, ALWAYS ask the user to provide the MPI rank decomposition. Always include the lattice size, which you can obtain from the getLatticeSize tool. Mention that you can help them choose a decomposition. Never ask for the total number of MPI ranks unless you are helping choose the geometry as part of the workflow below.
        - rank_geom is a blocking parameter. While rank_geom is unresolved, you MUST NOT ask about or advance to any other JobSubmissionParameters field.

        - If the user asks for help choosing a decomposition, follow this workflow exactly and do not deviate:

            1) You MUST obtain the number of MPI ranks explicitly from the user.
               - NEVER infer, derive, or guess the number of ranks from any other information.
               - Check the last user response. If it contains the number of ranks, use that value. If the user has not explicitly provided the number of ranks, ask only:
                 "How many MPI ranks will this job use?"

            2) After the user provides a valid integer number of ranks, you MUST immediately call getDefaultRankGeometry with that value.

            3) Your next response MUST present the suggested decomposition and ask for confirmation or an alternative decomposition.
               - Do not ask about any other parameter in this response.

            4) Stay in the rank_geom flow until the user either confirms the suggested decomposition or supplies a different valid decomposition. Repeat steps 2-4 if the user asks for a geometry with a different number of ranks.

          Never start this workflow unless the user has explicitly asked for help choosing the decomposition.
       
    - duration
         - if the user provides a value in any unit other than seconds (e.g. minutes, hours, etc), convert the user's response to seconds then output the value in seconds and explain that you converted to seconds on a separate line before your next question
           For example
           "You:  What is the duration of each run? You can answer in any unit.
            Human: 5 mins
            You: I've converted this to 300 seconds
                 <NEXT QUESTION>
           "

    - job_group         
         - In your response, on a separate line before your question, explain that this parameter distinguishes between different job collections. It is used as the name of a parent directory within the sandbox to keep different collections separate.

    - copy_out

      For this parameter, perform the following:
      1) For your first question, you MUST ask:
        "Do you want to copy results to a remote machine for postprocessing?"  

      2) If the user says yes:
          - Ask the user to provide the globus endpoint
          - Ask the user to obtain the base path

         If the user says no:
          - set copy_out to None
    
      Note that we are using NERSC's SuperFacility API to initiate these transfers, which also accepts special UUIDs "dtn", "hpss" or "perlmutter" in place of regular ID strings.

    -------------------------------------------
    Schema for fields you must populate
    -------------------------------------------

    The fields you must obtain values for are listed in the following schema:
    """ + json.dumps(JobSubmissionParameters.model_json_schema())

    
    tools = [agentGetKnownMachines,agentGetUserAccounts,
             getLatticeSize,getDefaultRankGeometry,
             agentGetMachineQueues]
    config = {"configurable": {"thread_id": "1"}}
    agent = create_agent(model=model, tools=tools, system_prompt=sys)

    check_complete_sys = """
    You must check the message history to determine if the user has provided answers to all fields in the following schema:
    """ + json.dumps(JobSubmissionParameters.model_json_schema()) + """
    Identify all parameters that the user has not specified and output them into the missing_parameters field of your output.
    If the user has specified all parameters, set missing_parameters to an empty list

    Your output must be provided according to the following schema:
    """ + json.dumps(ParameterCheck.model_json_schema())
    

    check_complete_agent = create_agent(model=model, system_prompt=check_complete_sys, response_format=ParameterCheck)
    
    output_sys = """
    You are an agent responsible for inserting information from the user into a structured output with the schema below.

    Use your message history to identify the user's decision for a parameter

    Determine whether the user has chosen a value by identifying whether the user's response is a statement describing a valid value for the parameter.

    You must identify the user's decision for all parameters

    - **Never** guess a parameter. The values should always be obtained from the user. Follow the User Query rules below for questions to the user.

    You must return JSON formated output in the following schema:
    """ + json.dumps(JobSubmissionParameters.model_json_schema()) 

    
    final_output_agent = create_agent(model=model, system_prompt=output_sys, response_format=JobSubmissionParameters)


    
    user_interactions = [ HumanMessage("Start your workflow") ]
    accepted = False
    obj = None
    while(accepted == False):
        try:
            resp = agent.invoke({ "messages": user_interactions }, config=config)
            resp_msg = resp['messages'][-1]

            #gpt-oss-120b with the AmSC LLM services sometimes runs ahead of itself with intervening blocks of reasoning output directly into the content in xml-like tags.
            #However it seems that the content before the first tag is the intended user output.
            if "<reasoning>" in resp_msg.content:
                resp_msg = AIMessage(content=resp_msg.content[:resp_msg.content.find('<reasoning>')])               
            
            user_interactions.append(resp_msg)

            resp_content = resp_msg.content
            
        except Exception as e:
            print("CAUGHT ERROR",e,"\n",vars(e))

            user_interactions.append(HumanMessage(f"Encountered an error: {e}"))
            continue

        if len(resp_content) == 0:
            user_interactions.append(HumanMessage(f"Your previous had no content, try again"))
            
        elif "<DONE>" in resp_content:
            #Use an agent to check that it really is done
            resp = check_complete_agent.invoke({"messages" : user_interactions})
            obj = resp['structured_response']
            if len(obj.missing_parameters) > 0:
                print("MISSING PARAMS", obj.missing_parameters)
                user_interactions.append(HumanMessage(f"The following parameters have not yet been specified by the user: { obj.missing_parameters }. Work with the user to determine these parameters."))
                continue
                
            #Formally parse the message chain into structured output
            resp = final_output_agent.invoke({ "messages": user_interactions })
            obj = resp['structured_response']           
            
            #Human validation
            output = f"Obtained:\n" + prettyPrintPydantic(obj)
            AgentPrint(output)
            
            accepted = queryYesNo("Is this correct?")
            
            if(accepted == False):
                reason = AgentInput("Explain what is wrong: ")
                user_interactions.append(HumanMessage(f"Your previous response was not accepted for the following reason: {reason}"))
            else:
                break
        else:
            #Obtain the user response
            user_resp = AgentInput(resp_content)
            user_interactions.append(HumanMessage(user_resp))

    AgentPrint("Submitting job to workflow manager...")
    enqueueStandardHadronsWorkflow(state, jman, obj.rank_geom, obj.machine, obj.job_group, obj.account, obj.queue, str(obj.duration), obj.copy_out)
