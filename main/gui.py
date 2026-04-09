from femtomeas.gui.server import app, setServerWorkflow, agentPrint, agentQuery
from femtomeas.gui.frontend import app_dash
from fastapi.middleware.wsgi import WSGIMiddleware
import femtomeas.meas_config_agent.common as common
from femtomeas.workflow_manager.manager_config import readManagerConfigStr
from femtomeas.workflow_manager.manager import JobManager

import os
import femtomeas.workflow_manager.globals as globals
globals.api_impl = os.getenv('FEMTOMEAS_API_IMPL', 'IRI')

from langchain_openai import ChatOpenAI
from femtomeas.meas_config_agent import agent

common.print_func = agentPrint
common.input_func = agentQuery
common.output_style = "markdown"

amsc_llm_0t = ChatOpenAI(
    model="gpt-oss-120b",
    base_url="https://api.i2-core.american-science-cloud.org/",
    temperature=0
)

llm = amsc_llm_0t

def workflow(config : dict):
    jman = None
    if config["use_workflow_manager"]:
        readManagerConfigStr(config["workflow_manager_config"])
        jman = JobManager("jobs.db")
        jman.start()
    
    if config["use_agent"]:
        query = "" if config["reload_state"] else agentQuery("Describe the observables you wish to compute")
        state = agent(query, llm, ckpoint_file=config["state_file"], reload_state=config["reload_state"])
        state.toHadronsXML().write("hadrons_run.xml")

    if jman:
        jman.stop() #will wait until the job queue is complete
                
        

setServerWorkflow(workflow)

app.mount("/", WSGIMiddleware(app_dash.server))

