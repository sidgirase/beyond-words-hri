#!/bin/bash
#SBATCH --job-name=hri_vla_sim
#SBATCH --account=ic
#SBATCH --partition=ice-gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00
#SBATCH --mem=32G
#SBATCH --output=logs/simulation_%j.out
#SBATCH --error=logs/simulation_%j.err

echo "Loading modules..."
module load anaconda3/2023.03
module load cuda/11.8

# We bypass conda activate entirely and use the absolute path to the python binary
# since SLURM can be very finicky with bash hooks.
echo "Starting VLA simulation in MuJoCo..."
export MUJOCO_GL="egl"
./vla_scratch_env/bin/python simulation/run_mujoco_experiments.py \
    --scenario all \
    --log_dir ./data_analysis/pilot_logs \
    --use_gui False 

echo "Simulation completed successfully!"
