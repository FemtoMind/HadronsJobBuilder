from femtomeas.workflow_manager.sfapi import *
from femtomeas.workflow_manager.api_general import *
from femtomeas.workflow_manager.api_tools import *
from femtomeas.workflow_manager.hadrons import *
import time
import os

key_path = os.getenv("NERSC_SFAPI_KEY_PATH")
if key_path == None:
    raise Exception("Expect environment variable NERSC_SFAPI_KEY_PATH")


machine = "Perlmutter"
#safe_dir = "/global/homes/c/ckelly/agent_safe_dir"
safe_dir = "/global/cfs/cdirs/mp13/ckelly/agent_safe_dir" #home is mounted read-only on PM
setupWorkflowAgent(key_path, { machine : safe_dir }  )

#assert testExecutablePrivileges(machine) == True

#print(queryMachineStatus.invoke("Perlmutter"))
#print(remoteLs.invoke( { "machine":"Perlmutter",  "path":"/global/homes/c/ckelly/" }))

#assert checkSafePath(machine, safe_dir + "/hello.txt") == True
#assert checkSafePath(machine, safe_dir + "/../hello.txt") == False

#test_file = "test_upload.txt"
#with open(test_file,"w") as f:
#    f.write("HELLO")

#assert uploadSmallFile.invoke( { "machine" : machine, "remote_path" : safe_dir + "/test1.txt", "local_path" : test_file } ) == True

if 0:
    caught_exception=False
    try:
       remoteMkdir(machine, "pooh", allow_unsafe=True)
    except Exception as e:
       print("Caught expected exception '",e,"'")
       caught_exception = True
    assert caught_exception

#ret = remoteMkdirUnsafe(machine, safe_dir + "/1/2")
#assert ret == 1 or ret == 2

setHadronsInfo({ "Perlmutter" : { "bin" : "/global/u2/c/ckelly/CPS/install_mpi_pm_new/Hadrons_pm_new/bin",    "env" : "source /global/u2/c/ckelly/CPS/bld/grid_pm_develop/sourceme.sh" } } )
#validateHadronsXML(machine, "hadrons_run.xml")

if 0:
    remoteMkdir(machine, safe_dir)
    uploadSmallFile(machine, safe_dir + "/run.xml", "hadrons_run.xml")

    script = f"""#!/bin/bash
    #SBATCH -C gpu
    #SBATCH -A mp13_g
    #SBATCH -q debug
    #SBATCH -N 1
    #SBATCH -G 1
    #SBATCH -t 5
    #SBATCH -o {safe_dir}/test_run.log

    source /global/u2/c/ckelly/CPS/bld/grid_pm_develop/sourceme.sh
    cd ${{SCRATCH}} #SQLite DB is apparently not writeable on compute nodes!?
    srun -n 1 /global/u2/c/ckelly/CPS/install_mpi_pm_new/Hadrons_pm_new/bin/HadronsXmlRun {safe_dir}/run.xml --mpi 1.1.1.1 --grid 8.8.8.8
    """

    print(script)
    jobid = executeBatchJob(machine, script)

    while(1):
        state = getJobState(machine, jobid)
        print(state)
        if state not in ("new", "queued", "active"):
            print("Detected job completion")
            break    
        time.sleep(10)

if 0:        
    jobid = submitHadronsJob(machine, "hadrons_run.xml", f"{safe_dir}/test_job", "mp13_g", "debug", "5", (16,16,8,8), (2,2,1,1))
    while(1):
        state = getJobState(machine, jobid)
        print(state)
        if state not in ("new", "queued", "active"):
            print("Detected job completion")
            break    
        time.sleep(10)

if 1:
    tid = globusCopyToMachine(machine, safe_dir, "dtn", "/global/cfs/cdirs/mp13/ckelly/globus_source_test_dir", block_until_complete=True)
#    for i in range(10):
#        print(globusTransferStatus(machine, tid))
#        time.sleep(2)

if 1:
    globusCopyFromMachine("dtn", "/global/cfs/cdirs/mp13/ckelly/globus_source_test_dir/copyback",  machine, safe_dir + "/test.dat", block_until_complete=True)
