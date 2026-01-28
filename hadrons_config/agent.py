import os
from .common import *
from .state import *
from .hadrons_xml import HadronsXML

def agent(query, model, ckpoint_file="state.json", reload_state=True):    
    if reload_state and os.path.exists(ckpoint_file):
        state = reloadStateCheckpoint(ckpoint_file)
        query = state.query
        print("Reloaded query from state file:", query)
    else:
        state = State()

    state.query = query
    messages = [HumanMessage(query)]
        
    print(state)

    if state.observables == None:
        Print("""
======================
IDENTIFY OBSERVABLES
======================
        """)       
        state.observables = identifyObservables(model, messages).observables
        checkpointState(state,ckpoint_file)

    #Augment messages with information derived from observables
    messages.append( HumanMessage("The following information has been derived regarding the observables we need to compute based on user input:\n" + json.dumps(TypeAdapter(List[ObservableInfo]).dump_python(state.observables)  , indent=2) ) )

    if state.actions == None:
        Print("""
======================
ACTIONS
======================
        """)       
        state.actions = identifyActions(model, messages).actions
        checkpointState(state,ckpoint_file)

    #Add actions information to messages
    #TODO: We don't need to pass forward all the parameter details of the actions, only the user_info and instance names are required
    messages.append( HumanMessage("The following action instances have been identified based on user input:\n" + json.dumps(TypeAdapter(List[ActionConfig]).dump_python(state.actions), indent=2) ) )        

    if state.sources == None:
        Print("""
======================
SOURCES
======================
        """)
        state.sources = identifySources(model, state, messages).sources
        checkpointState(state,ckpoint_file)

    if state.solvers == None:
        Print("""
======================
SOLVERS
======================
        """) 
        state.solvers = identifySolvers(model, state, messages).solvers
        checkpointState(state,ckpoint_file)

    #Add sources and solvers to messages
    messages.append( HumanMessage("The following source instances have been identified based on user input:\n" + json.dumps(TypeAdapter(List[SourceConfig]).dump_python(state.sources), indent=2) ) )        
    messages.append( HumanMessage("The following solver instances have been identified based on user input:\n" + json.dumps(TypeAdapter(List[SolverConfig]).dump_python(state.solvers), indent=2) ) )        

    if state.propagators == None:
        Print("""
======================
PROPAGATORS
======================
        """) 
        state.propagators = identifyPropagators(model, state, messages).propagators
        checkpointState(state,ckpoint_file)

    messages.append( HumanMessage("The following propagator instances have been identified based on user input:\n" + json.dumps(TypeAdapter(List[PropagatorConfig]).dump_python(state.propagators), indent=2) ) )               

    if state.observable_configs == None:
                
        Print("""
======================
OBSERVABLE CONFIGURATIONS
======================
        """)
        state.observable_configs = configureObservables(model, state, messages).observable_configs
        checkpointState(state,ckpoint_file)

    if state.gauge == None:
        Print("""
======================
GAUGE CONFIGURATIONS
======================
        """)
        state.gauge = identifyGaugeConfigs(model, messages)
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
