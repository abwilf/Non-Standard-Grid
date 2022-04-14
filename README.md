# Non-Standard Grid

This is a repo that allows you to run large scale grid searches on a cluster such as Atlas. At a high level, we want a program that takes in a set of hyperparameters, turns them into a grid search, runs all the different combinations in the grid across the cluster, collates the results, creates a report of the errors, and emails you when it finishes.  NSG does just that.  For each set of hyperparameters it creates a folder under a unique hash in results/{hash}, and creates subfolders for each combination's output.  When it has finished, it writes the results to `csv_results.csv`, along with the hyperparameters `hp.json` and a report of the errors `report.json`. As a side bonus, you can include files you'd like to compress into a tar for each HP search for perfect reproducibility later.

It is "non-standard" because unlike [Standard-Grid](https://github.com/A2Zadeh/Standard-Grid) (which is fantastic), this allows you to execute any kind of code you need in an sbatch script - including the important `ulimit` command and `singularity exec`. 

The functionality provided is incorporated to `alex_utils.py`, but is reproduced in `nsg.py` for clarity, in case you'd like to see what's happening under the hood.

## Installation
```
pip install pandas numpy requests tqdm h5py
```

Download Standard Grid from [here](https://github.com/abwilf/Standard-Grid) and change the paths in `alex_utils.py` to the one that corresponds to your system (i.e. find and replace `/work/awilf/Standard-Grid`). 

## Usage
To run a grid search with non-standard grid, you'll need two things: a program to run and a runfile which defines the grid search.
1. **The Program**: The basic requirements of this program are that it takes in arguments from Standard-Grid's argparser, writes results to `args.out_dir/results.json`, and writes `args.out_dir/success.txt` if it doesn't error out. I wrap this functionality in alex_utils.main_wrapper.  You can use the code below as a template `main.py` file.

```
from alex_utils import *

defaults = [
    ("--out_dir", str, "results/hash1"), # REQUIRED - results will go here
    ("--hp1", int, 1), # other arguments
    ('--hp2', int, 0),
]

def main(_gc):
    global gc
    gc = _gc

    # ... do whatever ...
    time.sleep(5)

    results = { # this will be different for you
        'hp1': [gc['hp1']],
        'hp2': [gc['hp2']],
        'accuracy': [gc['hp1']+gc['hp2']],
    }
    return results

if __name__ == '__main__':
    main_wrapper(main, defaults, results=True)
```

2. **The Runfile**: In the runfile (e.g. `run_nsg.py`), you define which hyperparameter combinations you'd like to search over, define the skeleton of your sbatch call, and pass all that to non-standard grid (`nsg`), which does the rest.  You can use the below (in `run_nsg.py`) as a template.  Make sure to look out for `TODO` markers.
```
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
    'command': 'python main.py',
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
    'dummy_program': 'python /work/awilf/utils/dummy.py', # give path to some program (empty works fine - e.g. touch /work/awilf/utils/dummy.py) you can run with sbatch immediately and it will do nothing - just to email you
    'tarfiles': ['main.py', 'README.md'], # choose some files you'd like to compress (tar) with each HP search so you can reproduce later.  If none, just use []

    # -- Probably don't customize --
    'skeleton': skeleton, # skeleton of sbatch command for each: nsg will add
    'hp': hp, # hyperparameters
    'command': skel_config['command'], # have to pass this in so nsg knows where to find and replace with hp flags
    'max_sbatch_ops': 8, # how many jobs running in parallel?  Good practice to keep this capped at 8
    'sleep_secs': 2, # how many seconds do you want it to sleep for before checking if there is space to submit another job?
    'num_chars_squeue': 3, # assume that squeue will only give us 3 characters of this hash.  Should be fine, because we're already filtering on andrewid
}
nsg(nsg_config)
```

3. Run the program with `run_nsg.py`. 

## Output
The program will create a tree like this for the hash of your hyperparameter combination
```bash
results/cb97ca32aaf0497/
    ├── 0
    │   ├── compute-0-18-err.txt
    │   ├── compute-0-18-out.txt
    │   ├── results.json
    │   └── success.txt
    ├── 1
    │   ├── compute-0-18-err.txt
    │   ├── compute-0-18-out.txt
    │   ├── results.json
    │   └── success.txt
    ├── 2
    ...
    ├── csv_results.csv
    ├── compressed.tar
    ├── hp.json
    ├── report.json
    └── run_scripts
        ├── 0.sh
        ├── 1.sh
        ├── 2.sh
        ...
    '''
```