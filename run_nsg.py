## Welcome to the run_nsg template!  You can customize this to get a grid search working.
# import sys; sys.path.append('/work/awilf/utils/'); from alex_utils import *
from alex_utils import *

## TODO: Make sure program takes inputs as --arg {arg_val}, not -arg or positional.  See main.py for example.

## TODO: DEFINE hyperparameters FOR SEARCH
hp = {
    'hp1': [1,2,3],
    'hp2': [6,7]
}

## Define sbatch skeleton
'''
This defines the skeleton of the script that will be generated to run with sbatch.  It should look like this.
#!/bin/bash
#SBATCH ...
#SBATCH ...

execute something
execute something else
command (e.g. python main.py -- just the program name: nsg will fill in the arguments)
'''

# -- TODO: CUSTOMIZE --
this_dir = '/work/awilf/nsg_test'
skel_config = {
    'command': 'python nsg_main.py',
    'gpu_partition': 'gpu_low',
    'num_gpu_per': 1, # gpus per task
    'mem_gb': 10, # 10 GB of mem allocated for each job
    'exclude_list': 'compute-2-9,compute-0-19',
    'mail_user': 'dummy@gmail.com',
    'mail_type': 'NONE', # for each of the jobs, do not send an email if they fail
    'runtime': '1-00:00', # how much runtime before atlas cuts it off (D-HH:MM)
}

## -- Probably don't customize --
skeleton = f'''#!/bin/bash
#SBATCH -p {skel_config['gpu_partition']}
#SBATCH --gres=gpu:{skel_config['num_gpu_per']}  # Use GPU
#SBATCH --mem {skel_config['mem_gb']}GB   # memory pool for all cores
#SBATCH --time {skel_config['runtime']}
#SBATCH --exclude={skel_config['exclude_list']}
#SBATCH --mail-type={skel_config['mail_type']}
#SBATCH --mail-user={skel_config['mail_user']}

cd {this_dir}
ulimit -v unlimited
{skel_config['command']}
'''

nsg_config = {
    # -- TODO: CUSTOMIZE --
    'andrewid': 'awilf',
    'results_path': f'{this_dir}/results', # path to ./results
    'overwrite': 1, # if this hash path already exists (this hyperparam combination has been tried), overwrite it?
    'hash_len': 15, # hashes are annoyingly long.  If you're not running a ton of tests, you can shorten the hash length (increased prob of collisions). -1 if you want full length.
    'dummy_program': 'python /work/awilf/utils/dummy.py', # give path to some program (probably empty) you can run with sbatch immediately and it will do nothing - just to email you
    
    # -- Probably don't customize --
    'skeleton': skeleton, # skeleton of sbatch command for each: nsg will add
    'hp': hp, # hyperparameters
    'command': skel_config['command'], # have to pass this in so nsg knows where to find and replace with hp flags
    'max_sbatch_ops': 8, # how many jobs running in parallel?  Good practice to keep this capped at 8
    'sleep_secs': 2, # how many seconds do you want it to sleep for before checking if there is space to submit another job?
    'num_chars_squeue': 3, # assume that squeue will only give us 3 characters of this hash.  Should be fine, because we're already filtering on andrewid
}
nsg(nsg_config)
