import json
from pydantic import BaseModel, Field, ConfigDict, NonNegativeInt, TypeAdapter
from typing import Literal, Union, List, Optional, Tuple

from .observable_info import *
from .observable_config import *
from .action_config import *
from .source_config import *
from .solver_config import *
from .propagator_config import *
from .gauge import *

def checkpointState(state, filename):
    #j = json.dumps({k: v.model_dump() for k, v in state.items()}, indent=2)
    j=json.loads(state.model_dump_json())
    with open(filename, 'w') as wr:
        wr.write(json.dumps(j,indent=2))

def reloadStateCheckpoint(filename):
    print("Reloading state checkpoint from",filename)
    with open(filename, 'r') as rd:
        j = rd.read()
    return State.model_validate_json(j)

class State(BaseModel):
    observables: List[ObservableInfo] | None = Field(None,description="The list of observables and associated relevant information")
    actions: List[ActionConfig] | None = Field(None,description="The list of action instances")
    sources: List[SourceConfig] | None = Field(None,description="The list of source instances")
    solvers: List[SolverConfig] | None = Field(None,description="The list of solver instances")
    propagators: List[PropagatorConfig] | None = Field(None,description="The list of propagator instances")
    observable_configs : List[ObservableConfig] | None = Field(None,description="The list of observable instances")
    gauge: GaugeFieldConfig | None = Field(None,description="The gauge configuration parameters")

    def isValidObservable(self, obs_name):
        for p in self.observables:
            if p.name == obs_name:
                return True
        return False

    def locateObservable(self, obs_name) -> ObservableInfo | None:
        for p in self.observables:
            if p.name == obs_name:
                return p
        return None
    
    def isValidAction(self, action_name):
        for p in self.actions:
            if p.name == action_name:
                return True
        return False
    
    def isValidSource(self, source_name):
        for p in self.sources:
            if p.name == source_name:
                return True
        return False

    def isValidSolver(self, solver_name):
        for p in self.solvers:
            if p.name == solver_name:
                return True
        return False   
    
    def isValidPropagator(self, prop_name):
        for p in self.propagators:
            if p.name == prop_name:
                return True
        return False
        
