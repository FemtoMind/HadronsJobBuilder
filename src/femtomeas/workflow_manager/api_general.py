import pathlib
import io
from .sfapi import *
from . import globals

def checkSafePath(machine: str, path: str):
    if globals.remote_workdir == None:
        raise Exception("setupWorkflowAgent has not been called")
    if machine not in globals.remote_workdir:
        raise Exception("Unknown machine")
    safe_p = pathlib.Path(globals.remote_workdir[machine]).resolve()
    path_p = pathlib.Path(path).resolve()
    tmp_p = pathlib.Path("/tmp")
    return path_p.is_relative_to(safe_p) or path_p.is_relative_to(tmp_p)

def testExecutablePrivileges(machine: str)-> bool:
    try:
        ret = remoteRun(machine, ["echo","'TEST'"])
        if ret.strip() == "TEST":
            return True
        else:
            return False
    except Exception as e:
        return False    

    
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
