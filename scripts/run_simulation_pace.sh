#!/bin/bash
#SBATCH --job-name=hri_vla_sim
#SBATCH --account=pace-ice
#SBATCH --partition=pace-ice-gpu  # Often required by PACE job_submit.lua
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

echo "Activating Conda Environment..."
source activate hri_vla_env

# Run the simulation experiments for the 4 clarification modes
echo "Starting VLA simulation in MuJoCo..."
python simulation/run_mujoco_experiments.py \
    --mode all \
    --log_dir ./data_analysis/pilot_logs \
    --use_gui False 

echo "Simulation completed successfully!"
