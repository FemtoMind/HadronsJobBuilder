from langgraph.func import entrypoint, task
import os
from .common import *
from .state import *
from .hadrons_xml import HadronsXML

@entrypoint()
def agent(args):
    messages = args["messages"]
    ckpoint_file = args["ckpoint_file"]
    reload_state = args["reload_state"]
    model = args["model"]
    
    state = State()
    if reload_state == "true":
        state = reloadStateCheckpoint(ckpoint_file)
    elif reload_state == "if_exists":
        if os.path.exists(ckpoint_file):
            state = reloadStateCheckpoint(ckpoint_file)
    elif reload_state != "false":
        raise Exception("Argument 'reload_state' must be 'true', 'false' or 'if_exists'")    

        
    print(state)

    if state.observables == None:
        print("""
======================
IDENTIFY OBSERVABLES
======================
        """)       
        state.observables = identifyObservables(model, messages).result().observables
        checkpointState(state,ckpoint_file)

    #Augment messages with information derived from observables
    messages.append( HumanMessage("The following information has been derived regarding the observables we need to compute based on user input:\n" + json.dumps(TypeAdapter(List[ObservableInfo]).dump_python(state.observables)  , indent=2) ) )
    print(messages[-1].content)
                               

    
    if state.actions == None:
        print("""
======================
ACTIONS
======================
        """)       
        state.actions = identifyActions(model, messages).result().actions
        checkpointState(state,ckpoint_file)

    #Add actions information to messages
    messages.append( HumanMessage("The following action instances have been identified based on user input:\n" + json.dumps(TypeAdapter(List[ActionConfig]).dump_python(state.actions), indent=2) ) )        
        
    if state.sources == None:
        print("""
======================
SOURCES
======================
        """)
        state.sources = identifySources(model, state, messages).result().sources
        checkpointState(state,ckpoint_file)
       
    if state.solvers == None:
        print("""
======================
SOLVERS
======================
        """) 
        state.solvers = identifySolvers(model, state, messages).result().solvers
        checkpointState(state,ckpoint_file)

    #Add sources and solvers to messages
    messages.append( HumanMessage("The following source instances have been identified based on user input:\n" + json.dumps(TypeAdapter(List[SourceConfig]).dump_python(state.sources), indent=2) ) )        
    messages.append( HumanMessage("The following solver instances have been identified based on user input:\n" + json.dumps(TypeAdapter(List[SolverConfig]).dump_python(state.solvers), indent=2) ) )        

        
    if state.propagators == None:
        print("""
======================
PROPAGATORS
======================
        """) 
        state.propagators = identifyPropagators(model, state, messages).result().propagators
        checkpointState(state,ckpoint_file)

    messages.append( HumanMessage("The following propagator instances have been identified based on user input:\n" + json.dumps(TypeAdapter(List[PropagatorConfig]).dump_python(state.propagators), indent=2) ) )               

    if state.observable_configs == None:
                
        print("""
======================
OBSERVABLE CONFIGURATIONS
======================
        """)
        state.observable_configs = configureObservables(model, state, messages).result().observable_configs
        checkpointState(state,ckpoint_file)

    if state.gauge == None:
        print("""
======================
GAUGE CONFIGURATIONS
======================
        """)
        state.gauge = identifyGaugeConfigs(model, messages).result()
        checkpointState(state,ckpoint_file)
        
    #XML output
    xml = HadronsXML()
    xml.setRunID(1234)
    
    state.gauge.setXML(xml)
    for a in state.actions:
        a.setXML(xml)
    for s in state.sources:
        s.setXML(xml)
    for s in state.solvers:
        s.setXML(xml)
    for p in state.propagators:
        p.setXML(xml)

    #Temporary; add a zero-momentum point sink for two-point functions
    #TODO: Have the observables agent also construct sinks as needed
    snk = xml.addModule("point_sink_zerop", "MSink::ScalarPoint")
    HadronsXML.setValue(snk, "mom", "0. 0. 0.")
        
    for o in state.observable_configs:
        o.setXML(xml)
    
    xml.write("hadrons_run.xml")
