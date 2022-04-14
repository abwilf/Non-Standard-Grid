# example main.py
# import sys; sys.path.append('/work/awilf/utils/'); from alex_utils import *
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

    if gc['hp1'] == 1:
        assert False, 'fail!'
    
    results = {
        'hp1': [gc['hp1']],
        'hp2': [gc['hp2']],
        'accuracy': [gc['hp1']+gc['hp2']],
    }
    return results

if __name__ == '__main__':
    main_wrapper(main,defaults, results=True)

