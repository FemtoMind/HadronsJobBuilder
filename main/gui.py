from femtomeas.gui.server import app, setServerWorkflow, agentPrint, agentQuery, workflowManagerLogGUI, workflowAPIlogGUI
from femtomeas.gui.frontend import app_dash
from fastapi.middleware.wsgi import WSGIMiddleware
import femtomeas.meas_config_agent.common as common
from femtomeas.workflow_manager.manager_config import readManagerConfigStr
from femtomeas.workflow_manager.manager import JobManager
from femtomeas.workflow_manager.hadrons_workflow import enqueueStandardHadronsWorkflow

import time
import os
import json
import femtomeas.workflow_manager.globals as globals
import femtomeas.workflow_manager.logging as wfman_logging

globals.api_impl = os.getenv('FEMTOMEAS_API_IMPL', 'IRI')

from langchain_openai import ChatOpenAI
from femtomeas.meas_config_agent import agent

common.print_func = agentPrint
common.input_func = agentQuery
common.output_style = "markdown"

wfman_logging.wfman_log_func = workflowManagerLogGUI
wfman_logging.api_log_func = workflowAPIlogGUI

amsc_llm_0t = ChatOpenAI(
    model="gpt-oss-120b",
    base_url="https://api.i2-core.american-science-cloud.org/",
    temperature=0
)

llm = amsc_llm_0t

def workflow(config : dict):
    jman = None
    if config["use_workflow_manager"]:
        db_file = "jobs.db"
        workflowManagerLogGUI(f"Starting job manager with database {db_file} and config:\n{ json.dumps( json.loads(config["workflow_manager_config"]), indent=4) }")
        
        readManagerConfigStr(config["workflow_manager_config"])
        jman = JobManager(db_file)
        jman.start()
    
    if config["use_agent"]:
        query = "" if config["reload_state"] else agentQuery("Describe the observables you wish to compute")
        state = agent(query, llm, ckpoint_file=config["state_file"], reload_state=config["reload_state"])
        #state.toHadronsXML().write("hadrons_run.xml")

        if config["use_workflow_manager"]:
            #For now we just use Perlmutter and an 8^4 configuration with 1 rank for simplicity
            mpi = (1,1,1,1)
            grid= (8,8,8,8)
            machine = "Perlmutter"
            agentPrint("Submitting job to workflow manager...")            
            enqueueStandardHadronsWorkflow(state, jman, mpi, grid, machine, "test_group", "amsc013_g", "debug", "300")


        
    if jman:
        time.sleep(10)
        jman.stop() #will wait until the job queue is complete
        workflowManagerLogGUI(f"Job manager has finished")
        

setServerWorkflow(workflow)

app.mount("/", WSGIMiddleware(app_dash.server))

