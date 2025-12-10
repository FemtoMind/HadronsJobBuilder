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
