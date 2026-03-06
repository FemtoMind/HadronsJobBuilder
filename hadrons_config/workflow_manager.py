from langchain_core.messages import BaseMessage
from langchain.messages import (
    SystemMessage,
    HumanMessage,
    ToolCall,
    AIMessage
)

from pydantic import BaseModel, Field, ConfigDict, NonNegativeInt, TypeAdapter
from typing import Literal, Union, List, Optional, Tuple
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy
from langchain.agents import create_agent
from .hadrons_xml import HadronsXML
import json
from .common import *
import os
import io
import pathlib

######Tools
# For now we just wrap functionality provided by the NERSC SFAPI, to be replaced by IRI API

import sfapi_client
from sfapi_client import Client
from sfapi_client.compute import Machine
import sfapi_client.paths

known_machines = {  "Perlmutter" : { "sfapi_enum" : Machine.perlmutter }  }

sfapi_key_path=None
remote_workdir=None

def setupWorkflowAgent(key_path, work_dir : dict):
    """
    Setup the workflow agent
    Args:
       key_path: The full path to the key file in .pem format (with username on the first line) as per https://nersc.github.io/sfapi_client/quickstart/#__tabbed_9_2  "Storing keys in files"
       work_dir: The remote work directories, by machine as a dict, e.g. { "Perlmutter" : "/path/to/dir" }.  The agent is only allowed to modify the contents of files within this directory or its children
    """
    global sfapi_key_path
    global remote_workdir
    sfapi_key_path = key_path
    remote_workdir=work_dir

sfapi_clients = {}
    
def sfAPIclientExecute(machine: str, what):
    if machine not in known_machines:
        raise Exception("Invalid machine name")
    m = known_machines[machine]["sfapi_enum"]

    global sfapi_clients
    if machine in sfapi_clients:
        client = sfapi_clients[machine]
    else:    
        if sfapi_key_path == None:
            raise Exception("setupWorkflowAgent has not been called")
        client = Client(key = sfapi_key_path)
        sfapi_clients[machine] = client
    return what(client, m)


def remoteRun(machine: str, args : str | List[str] )-> str:
    """
    Run a command on the remote machine login node
    """
    return sfAPIclientExecute(machine, lambda client, m: client.compute(m).run(args))
    
def testExecutablePrivileges(machine: str)-> bool:
    try:
        ret = remoteRun(machine, ["echo","'TEST'"])
        if ret.strip() == "TEST":
            return True
        else:
            return False
    except e:
        return False    
                             
    
@tool
def queryMachineStatus_t(machine: str)-> bool:
    """
    Query the status of a machine
    Args:
       machine - The name of the machine. Valid values are 'Perlmutter'
    Return:
       A bool indicating whether the machine up (True) or down (False)
    """
    def _doit(client, m):
        status = client.compute(m)
        return True if status.status == sfapi_client.StatusValue.active else False
        
    return sfAPIclientExecute(machine, _doit)

@tool
def remoteLs_t(machine: str, path: str)-> List[str]:
    """
    Query the contents of a path on a given machine
    Args:
       machine - The name of the machine. Valid values are 'Perlmutter'
       path - The absolute path. If a directory, ensure the path ends in '/' to get the directory contents.
    Return:
       A list of files in the directory
    """
    def _doit(client, m):
        pths = client.compute(m).ls(path)
        return [ p.name for p in pths ]
        
    return sfAPIclientExecute(machine, _doit)

def checkSafePath(machine: str, path: str):
    if remote_workdir == None:
        raise Exception("setupWorkflowAgent has not been called")
    if machine not in remote_workdir:
        raise Exception("Unknown machine")
    safe_p = pathlib.Path(remote_workdir[machine]).resolve()
    path_p = pathlib.Path(path).resolve()
    tmp_p = pathlib.Path("/tmp")
    return path_p.is_relative_to(safe_p) or path_p.is_relative_to(tmp_p)


def remoteMkdir(machine: str, path: str, create_parents = True, allow_unsafe = False)-> int:
    """
    Create a directory on the remote machine. This is an unsafe action as it is not confined to the sandbox directory, and thus should not be exposed as a tool without safeguards
    Args:
           allow_unsafe - Allow uploading to directories other than within the sandbox
    Return: 0 if the operation failed, 1 if the directory was created, 2 if it already existed
    
    """
    if not allow_unsafe and not checkSafePath(machine, path):
        raise Exception("Path is not a subdirectory of the sandbox path")

    if not pathlib.Path(path).is_absolute():
        raise Exception("Path must be absolute")

    cmd = f"[ -d '{path}' ] && echo 'Directory exists' || mkdir {'-pv' if create_parents else '-v'} {path}"
    
    #ret = remoteRun(machine, [ "mkdir", "-pv" if create_parents else "-v", path ]).strip().split('\n')
    ret = remoteRun(machine, cmd).strip().split('\n')

    if ret[-1] == 'Directory exists':
        return 2
    elif ret[-1] == f"mkdir: created directory '{path}'":
        return 1
    else:
        print(ret)
        return 0
    
@tool
def remoteMkdir_t(machine: str, path: str, create_parents : bool = True)-> int:
    """
    Create a directory on the remote machine. The path must be a relative of the sandbox directory
    Args:
       machine - The name of the machine. Valid values are 'Perlmutter'
       path - The absolute path on the remote machine
       create_parents - If True, parent directories will be created as needed, if False the new directory must be a child of an existing directory        
    Return: 0 if the operation failed, 1 if the directory was created, 2 if it already existed
    """
    return remoteMkdir(machine, path, create_parents, allow_unsafe = False)
    

    
def uploadBytes(machine: str, remote_path: str, content: io.BytesIO, allow_unsafe = False) -> bool:
    """
    Upload file contents as bytes to a remote path
    Args:
       machine - The name of the machine. Valid values are 'Perlmutter'
       remote_path - The absolute path on the remote machine
       content - The file contents as binary
       allow_unsafe - Allow uploading to directories other than within the sandbox
    Return:
       True if successful, False otherwise
    """
    if not allow_unsafe and not checkSafePath(machine, remote_path):
        raise Exception("Path is not below the privileged directory")
    
    def _doit(client, m):
        pth = sfapi_client.paths.RemotePath(path=remote_path, compute=client.compute(m))        
        return pth.upload(content).is_file()
    return sfAPIclientExecute(machine, _doit)

def uploadSmallFile(machine: str, remote_path: str, local_path: str, allow_unsafe = False) -> bool:
    """
    Upload a small file to a remote path
    Args:
       machine - The name of the machine. Valid values are 'Perlmutter'
       remote_path - The absolute path on the remote machine
       local_path - The path on the local machine
       allow_unsafe - Allow uploading to directories other than within the sandbox
    Return:
       True if successful, False otherwise
    """
    with open(local_path, "rb") as fh:
        return uploadBytes(machine, remote_path, io.BytesIO( fh.read() ) )


@tool
def uploadSmallFile_t(machine: str, remote_path: str, local_path: str) -> bool:
    """
    Upload a small file to a remote path
    Args:
       machine - The name of the machine. Valid values are 'Perlmutter'
       remote_path - The absolute path on the remote machine
       local_path - The path on the local machine
    Return:
       True if successful, False otherwise
    """
    return uploadSmallFile(machine, remote_path, local_path, allow_unsafe=False)



#SFAPI returns job handles, IRI uses job IDs
sfapi_jobs = {}

def executeBatchJob(machine: str, script: str) -> str:
    """
    Execute a batch script on the machine
    """    
    def doit_(client, m):
        return client.compute(m).submit_job(script)

    job = sfAPIclientExecute(machine, doit_)
    global sfapi_jobs
    sfapi_jobs[str(job.jobid)] = job
    return str(job.jobid)

sfapi_state_map = { "CONFIGURING" : "new", "PENDING" : "queued", "RUNNING" : "active", "COMPLETED" : "completed", "FAILED" : "failed", "CANCELLED" : "cancelled", "COMPLETING" : "active" }

    
    #IRI API: 
    #0"new"
    #1"queued"
    #2"active"
    #3"completed"
    #4"failed"
    #5"canceled"

    #SFAPI:
    # CONFIGURING = "CONFIGURING"

    # RESV_DEL_HOLD = "RESV_DEL_HOLD"
    # REQUEUE_FED = "REQUEUE_FED"
    # REQUEUE_HOLD = "REQUEUE_HOLD"
    # REQUEUED = "REQUEUED"

    # CANCELLED = "CANCELLED"
    # COMPLETED = "COMPLETED"
    # COMPLETING = "COMPLETING"

    # DEADLINE = "DEADLINE"
    # FAILED = "FAILED"
    # NODE_FAIL = "NODE_FAIL"
    # OUT_OF_MEMORY = "OUT_OF_MEMORY"
    # PENDING = "PENDING"
    # PREEMPTED = "PREEMPTED"
    # RUNNING = "RUNNING"
    # RESIZING = "RESIZING"
    # REVOKED = "REVOKED"
    # SIGNALING = "SIGNALING"
    # SPECIAL_EXIT = "SPECIAL_EXIT"
    # STAGE_OUT = "STAGE_OUT"
    # STOPPED = "STOPPED"
    # SUSPENDED = "SUSPENDED"
    # BOOT_FAIL = "BOOT_FAIL"
    # TIMEOUT = "TIMEOUT"

   
def getJobState(machine: str, jobid: str) -> str:
    if jobid not in sfapi_jobs.keys():
        raise Exception("Job is not in the list of known jobs")
    job = sfapi_jobs[jobid]
    job.update()
    if job.state not in sfapi_state_map.keys():
        raise Exception(f"Unknown job state: {str(job.state)}")
    return sfapi_state_map[job.state]

def cancelJob(machine: str, jobid: str):
    if jobid not in sfapi_jobs.keys():
        raise Exception("Job is not in the list of known jobs")
    job = sfapi_jobs[jobid]
    job.cancel()
    

machine_globus_endpoints = { "Perlmutter" : "perlmutter" }
    
def globusCopyToMachine(machine: str, dest_path : str,
                    source_endpoint: str, source_path : str,
                    allow_unsafe=False):
    if not allow_unsafe and not checkSafePath(machine, dest_path):
        raise Exception("Attempting to copy data to a location outside of the sandbox")
    if machine not in machine_globus_endpoints.keys():
        raise Exception("Unknown machine endpoint")
    
    trans_args = { "source_uuid" : source_endpoint, "target_uuid" : machine_globus_endpoints[machine],
                   "source_dir" : source_path, "target_dir" : dest_path }
    print(trans_args)
    def doit_(client, m):
        return client.post("storage/globus/transfer", data=trans_args)
    
    ret = sfAPIclientExecute(machine, doit_)
    print(ret)

    
###################################################################
#Tools for Hadrons

hadrons_info = None

def setHadronsInfo(hadrons_info_ : dict):
    """
    Provide the information necessary to run Hadrons on a remote machine
    Args:
       hadrons_info_ : dict    machine_name -> {
                                                 "bin" : "/path/to/hadrons/bin/dir",
                                                 "env" (optional) : "Command line instructions to set up environment, e.g.  module load hadrons" }
                                               }
    """
    for m in hadrons_info_.keys():
        if m not in known_machines:
            raise Exception("Invalid machine name")
        if "bin" not in hadrons_info_[m]:
            raise Exception("Bin dir must be provided")
        if "env" not in hadrons_info_[m]:
            hadrons_info_[m]["env"] = ""
    global hadrons_info
    hadrons_info = hadrons_info_
        

def validateHadronsXML(machine: str, hadrons_xml_file : str) -> bool:
    if hadrons_info == None:
        raise Exception("Must run setHadronsInfo")
    if machine not in hadrons_info.keys():
        raise Exception("Invalid machine")

    #create scratch dir in sandbox if not there already
    scratch_dir = remote_workdir[machine] + "/scratch"
    remoteMkdirUnsafe(machine, scratch_dir)
    
    tmp_file = scratch_dir + "/hadrons_validate.xml"
    uploadSmallFile(machine, tmp_file, hadrons_xml_file)
    ret = remoteRun(machine,  f'{ hadrons_info[machine]["env"] }; { hadrons_info[machine]["bin"] }/HadronsXmlValidate { tmp_file }').strip().split('\n')

    if "Application valid" in ret[-1]:
        return True
    else:
        print(ret)
        return False

def defaultRankGeom(ranks : int, grid : Tuple[int,int,int,int]):
    #rem = ranks
    # mu = 0
    # 
    # while(rem % 2 != 1):
    #     grid[mu] *= 2
    #     rem = rem // 2
    #     mu = (mu + 1) % 4
    # grid[mu] *= rem

    rem = ranks
    geom = [1,1,1,1]
    grid_rem = list(grid)
    while(rem % 2 != 1):
        #Find a grid direction divisible by 2 and that has the smallest number of ranks in that direction
        smu=None
        for mu in range(4):
            if grid_rem[mu] % 2 == 0 and ( True if smu == None else geom[mu] < geom[smu] ):
                smu = mu
        if smu == None:
            raise Exception(f"Remaining ranks is {rem} but remaining grid {grid_rem} has no directions divisible by 2")
        
        geom[smu] *= 2
        grid_rem[smu] = grid_rem[smu] // 2        
        rem = rem // 2

    smu = None
    for mu in range(4):
        if grid_rem[mu] % rem == 0 and ( True if smu == None else geom[mu] < geom[smu] ):
            smu = mu
    if smu == None:
        raise Exception(f"Remaining ranks is {rem} but remaining grid {grid_rem} has no directions divisible by it")
    geom[smu] *= rem
    grid_rem[smu] = grid_rem[smu] // rem
   
    prod = 1    
    for mu in range(4):
        prod *= geom[mu]
        assert geom[mu] * grid_rem[mu] == grid[mu]
        
    assert(prod == ranks)
    
    return geom, grid_rem

def sizesToGridArgList(sizes : List[int]):
    if(len(sizes) == 0):
        return ""
    
    out = str(sizes[0])
    for i in range(1,len(sizes)):
        out = out + f".{sizes[i]}"
    return out

def submitHadronsJob(machine: str,
                     hadrons_xml_file : str,
                     job_run_dir : str,
                     account : str,
                     queue : str,
                     time : str,
                     grid : Tuple[int, int, int, int], 
                     mpi : Tuple[int, int, int, int] | None = None, 
                     ranks = None
                     ):
    if hadrons_info == None:
        raise Exception("Must run setHadronsInfo")
    if machine not in hadrons_info.keys():
        raise Exception("Invalid machine")
    
    if ranks == None and mpi == None:
        raise Exception("Must specify either the rank geometry or the total number of ranks")
    elif ranks == None:
        ranks = 1
        for mu in range(4):
            ranks *= mpi[mu]
            if grid[mu] % mpi[mu] != 0:
                raise Exception(f"Global lattice size {grid[mu]} in direction {mu} does not divide evenly over {mpi[mu]} ranks")
    elif mpi == None:
        mpi = defaultRankGeom(ranks, grid)

    if not checkSafePath(machine, job_run_dir):
        raise Exception(f"Provided job path {job_run_dir} is not in the sandbox")

    remoteMkdir(machine, job_run_dir)
    uploadSmallFile(machine, f"{job_run_dir}/run.xml", hadrons_xml_file)
    
    grid_str = sizesToGridArgList(grid)
    mpi_str = sizesToGridArgList(mpi)

    ###################################
    if machine == "Perlmutter":
        nodes = (ranks + 3) // 4
        script=f"""#!/bin/bash
#SBATCH -q {queue}
#SBATCH -C gpu
#SBATCH -A mp13_g
#SBATCH --ntasks-per-node=4
#SBATCH -c 32
#SBATCH --exclusive
#SBATCH --gpus-per-task=1
#SBATCH --gpu-bind=none
#SBATCH -N {nodes}
#SBATCH -t {time}
#SBATCH -o {job_run_dir}/run.log
        
BIND="--cpu-bind=verbose,map_ldom:3,2,1,0"
export MPICH_OFI_NIC_POLICY=GPU

#Hadrons uses an SQLite database that has I/O failures on Lustre. We need to actually run in a temporary directory then move everything back        
SCRATCH_DIR=${{SCRATCH}}/${{SLURM_JOB_ID}}
mkdir -p ${{SCRATCH_DIR}}        
cd ${{SCRATCH_DIR}}
        
cat <<EOF > wrap.sh
#!/bin/bash
export CUDA_VISIBLE_DEVICES=\\${{SLURM_LOCALID}}  
echo "Rank \\${{SLURM_PROCID}}, local rank \\${{SLURM_LOCALID}} : visible devices \\${{CUDA_VISIBLE_DEVICES}}"
cd ${{SCRATCH_DIR}}
\\$*
EOF
        
chmod u+x wrap.sh
{ hadrons_info[machine]["env"] }
        
srun ${{BIND}} -n {ranks} ./wrap.sh { hadrons_info[machine]["bin"] }/HadronsXmlRun {job_run_dir}/run.xml --mpi {mpi_str} --grid {grid_str} --accelerator-threads 8 --shm 3072 --device-mem 15360 --threads 8 --log Iterative,Message,Error,Warning,Performance --comms-overlap --comms-concurrent --shm-mpi 1
mv ${{SCRATCH_DIR}}/* {job_run_dir}/
rmdir ${{SCRATCH_DIR}}        
"""
    #######################################
        
    remote_script_path = f"{job_run_dir}/batch_script.sh"
    with open('/tmp/batch_script.sh', 'w') as f:
        f.write(script)
    uploadSmallFile(machine, remote_script_path, "/tmp/batch_script.sh")
        
    return executeBatchJob(machine, remote_script_path)
    


#=================================================================
def manageWorkflow(model, output_xml_file):
    pass
