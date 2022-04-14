#!/bin/bash
#SBATCH -p cpu_low
#SBATCH --mem 10GB   # memory pool for all cores
#SBATCH --time 1-00:00
#SBATCH --exclude=compute-2-9,compute-0-19
#SBATCH --mail-type=NONE
#SBATCH --mail-user=dummyblah123@gmail.com
#SBATCH --job-name 0_cb97ca32aaf0497        # %j specifies JOB_ID
#SBATCH -o /work/awilf/nsg_test/results/cb97ca32aaf0497/0/%N-out.txt        # STDOUT
#SBATCH -e /work/awilf/nsg_test/results/cb97ca32aaf0497/0/%N-err.txt        # STDERR

cd /work/awilf/nsg_test
ulimit -v unlimited
python main.py --hp1 1 --hp2 6 --out_dir /work/awilf/nsg_test/results/cb97ca32aaf0497/0
