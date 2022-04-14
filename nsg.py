
#### NON-STANDARD GRID (NSG) ####
def get_grid(hp):
    if 'subsets' in hp.keys():
        all_grids = []
        subsets = hp['subsets']
        del hp['subsets']

        for sub in subsets:
            sub_hp = {**hp, **sub}
            keys, vals = zip(*list(sub_hp.items()))
            grid = [{k:v for k,v in zip(keys,elt)} for elt in list(itertools.product(*vals))]
            all_grids.extend(grid)

        grid = all_grids
    else:
        keys, vals = zip(*list(hp.items()))
        grid = [{k:v for k,v in zip(keys,elt)} for elt in list(itertools.product(*vals))]
    
    return grid

def get_ops(hash_, config):
    return os.popen(f'squeue | grep {config["andrewid"]} | grep {hash_[:config["num_chars_squeue"]]}').read()

def get_num_ops(hash_, config):
    return get_ops(hash_, config).count('\n')

def get_id(path):
    return path.split('/')[-1].replace('.sh', '')

def create_dir_structure(hash_, hash_path, grid, config):
    ## Create directory structure and runscripts within results/, looks like this at the end (after err and out files have been written)
    '''
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
    print('Length of grid:', len(grid))
    if isdir(hash_path):
        if not config['overwrite']:
            print(f'Hash path {hash_path} exists and overwrite is not specified. Exiting now.')
            exit()
        else:
            print(f'Removing and rewriting hash path {hash_path}')
            rmrf(hash_path)

    run_scripts_dir = join(hash_path, 'run_scripts')
    mkdirp(run_scripts_dir)

    to_run = []
    for i,comb in enumerate(grid):
        out_dir = join(hash_path, str(i))
        mkdirp(out_dir)

        hp_to_add = ' '.join([f'--{k} {v}' for k,v in comb.items()]) + f' --out_dir {out_dir}'

        # modify skeleton to create final sh file: add output files and hp flags
        skel = config['skeleton'].split('\n')
        split_idx = np.max([i for (i,elt) in enumerate(skel) if '#SBATCH' in elt])
        before = skel[:split_idx+1]
        after = skel[split_idx+1:]
        middle = [
            f'#SBATCH --job-name {i}_{hash_}        # %j specifies JOB_ID',
            f'#SBATCH -o {join(out_dir,"%N-out.txt")}        # STDOUT, says which machine in case you want to exclude',
            f'#SBATCH -e {join(out_dir,"%N-err.txt")}        # STDERR',
        ]
        skel = '\n'.join([*before, *middle, *after])
        skel = skel.replace(config['command'], f"{config['command']} {hp_to_add}")
        
        run_script = join(run_scripts_dir, f'{i}.sh')
        to_run.append(run_script)
        write_txt(run_script, skel)
    
    return to_run

def submit_scripts(to_run, in_progress, hash_, config):
    num_sbatch_ops = get_num_ops(hash_, config)
    while num_sbatch_ops <= config['max_sbatch_ops'] and len(to_run) > 0:
        run_script = to_run.pop()
        in_progress.append(run_script)
        os.popen(f'sbatch {run_script}').read()
        num_sbatch_ops = get_num_ops(hash_, config)

def monitor(to_run, in_progress, finished, tot_num, hash_, config):
    submit_scripts(to_run, in_progress, hash_, config)
    if len(to_run) == 0 and len(in_progress)==0:
        config['gridsearch_complete'] = True
        return in_progress, finished

    sbatch_ops = get_ops(hash_, config)
    finished.extend([elt for elt in in_progress if f'{get_id(elt)}_{hash_[:config["num_chars_squeue"]]}' not in sbatch_ops])
    in_progress = [elt for elt in in_progress if f'{get_id(elt)}_{hash_[:config["num_chars_squeue"]]}' in sbatch_ops]

    num_sbatch_ops = get_num_ops(hash_, config)
    print(f'To run: {100*len(to_run) / tot_num:.1f}%\tIn progress: {100*len(in_progress)/tot_num:.1f}%\tFinished: {100*len(finished)/tot_num:.1f}%', end='\r')

    time.sleep(config['sleep_secs'])
    return in_progress, finished

def submit_monitor_sbatch(to_run, hash_, config):
    # Submit and monitor script progress (not too many at at time)
    in_progress, finished = [], []
    tot_num = len(to_run)
    config['gridsearch_complete'] = False

    print(f'\n\nhash=\'{hash_}\'\n')
    print(f'\n## Status ## \nRunning {len(to_run)} scripts total (max {config["max_sbatch_ops"]} at a time)\n')

    while not config['gridsearch_complete']:
        in_progress, finished = monitor(to_run, in_progress, finished, tot_num, hash_, config)

    print('\n\nGrid Search Complete!')

def collate_results(hash_, hash_path, grid, config):
    # Consolidate json files into a single csv
    csv_path = join(hash_path, 'csv_results.csv')
    print(f'Writing csv to \n{csv_path}\n')

    ld = {} # list of dicts
    for path in pathlib.Path(join(config["results_path"], hash_)).rglob('*.json'):
        id = int(str(path).split('/')[-2])
        hp_comb = grid[id]
        ld[id] = {**load_json(path), **{'_'+k:v for k,v in hp_comb.items()}}

    df = pd.DataFrame(ld).transpose()
    df.to_csv(csv_path)

    hp_path = join(hash_path, 'hp.json')
    save_json(hp_path, config['hp'])

def compile_error_report(hash_path, grid):
    # compile error report
    report = {
        'num_combs': len(grid),
        'num_successful': 0,
        'num_failed': 0,
        'errors': {}
    }
    for i in range(len(grid)):
        if 'success.txt' not in [elt.split('/')[-1] for elt in glob(join(hash_path, f'{i}', '*'))]:
            report['num_failed'] += 1
            report['errors'][i] = {
                'hp': grid[i],
                'err': open([elt for elt in glob(join(hash_path, f'{i}', '*')) if 'err.txt' in elt][0]).read(),
                'node': [elt for elt in glob(join(hash_path, f'{i}', '*')) if 'err.txt' in elt][0].split('-err')[0],
            }
        else:
            report['num_successful'] += 1

    if report['num_failed'] > 0:
        print(f'###\n!!! ALERT !!!\nThere were some errors.  Please check the report for a description:\n{join(hash_path, "report.json")}\n###')
    
    save_json(join(hash_path, 'report.json'), report)

def email_complete(config):
    os.popen(f'sbatch --mail-type=END --mail-user=dummyblah123@gmail.com --wrap "{config["dummy_program"]}"')

def compress_files(hash_path, config):
    if len(config['tarfiles']) > 0:
        write_tar(join(hash_path, 'compressed.tar'), config['tarfiles'])
    

def nsg(config):
    '''
    Requires a runfile (e.g. /work/awilf/utils/run_nsg.py)
    '''
    rt = Runtime()
    hash_ = hashlib.sha1(json.dumps(config['hp'], sort_keys=True).encode('utf-8')).hexdigest()[:config['hash_len']]
    hash_path = join(config['results_path'], hash_)

    grid = get_grid(config['hp'])
    to_run = create_dir_structure(hash_, hash_path, grid, config)
    submit_monitor_sbatch(to_run, hash_, config)
    collate_results(hash_, hash_path, grid, config)
    compile_error_report(hash_path, grid)
    email_complete(config)
    compress_files(hash_path, config)

    print(f'\nhash=\'{hash_}\'\n\n')

    rt.get()
####

