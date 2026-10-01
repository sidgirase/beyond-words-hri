# Beyond Words: Evaluating Verbal and Gestural Clarification Strategies

This repository contains the codebase for the CS-7633 HRI Fall 2026 project. The project evaluates multi-modal clarification strategies (verbal, gestural, hybrid) when a robot encounters ambiguous instructions.

## Mid-Point Goal (Next Week)
**Goal:** Present functioning code and initial output by the midpoint submission (10/20-22).
**Deliverables:**
1. 4 modes of clarification functioning in simulation.
2. Pilot test completed to verify urgency and scoring metrics.

## Repository Structure
```
HRI_Project/
├── docs/                # Proposals, papers, survey drafts
├── interface/           # Gamified chat/audio GUI
├── simulation/          # MuJoCo Stretch Simulation Stack (Hello Robot)
├── physical_robot/      # Code for actual Stretch 2/3 robot deployment
├── data_analysis/       # Scripts to analyze objective/subjective logs
└── scripts/             # PACE-ICE SLURM submission scripts
```

## Team Roles & Task Division (P1, P2, P3)

### P1: Om Shivam Verma (Simulation & VLA Integration)
- **Mid-Point Tasks:** 
  - Finalize VLA deployment on the simulation-based robot.
  - Implement the **4 clarification modes** (Immediate, Ask, Gesture, Hybrid) in MuJoCo.
- **Run Experiments:** `simulation/run_mujoco_experiments.py`

### P2: Rena Nakashima (Interface & User Study)
- **Mid-Point Tasks:** 
  - Build the gamified chat/audio GUI for the human-robot interaction.
  - Set up data logging for objective (time, success) and subjective metrics.
- **Run Experiments:** `interface/start_gui.py`

### P3: Siddhesh Girase (Metrics & Physical Readiness)
- **Mid-Point Tasks:** 
  - Design and force the **scoring metric** to ensure ambiguity/urgency holds in the pilot.
  - Test initial translation of simulated gestures to physical Stretch limits (pre-study).
- **Run Experiments:** `data_analysis/pilot_scoring.py`

---

## Running Experiments & PACE-ICE Setup

For computationally heavy tasks (e.g., running the VLA model or MuJoCo simulations), we utilize the **PACE-ICE** cluster. 

### PACE-ICE Quick Start
1. Log into PACE-ICE: `ssh <username>@login-ice.pace.gatech.edu`
2. Navigate to your scratch directory and clone this repo:
   ```bash
   cd ~/scratch
   git clone <repo_url>
   cd HRI_Project
   ```
3. Submit the SLURM job to start the simulation experiments:
   ```bash
   sbatch scripts/run_simulation_pace.sh
   ```

### Local Setup
If running locally on a dedicated machine:
```bash
pip install -r requirements.txt
python simulation/run_mujoco_experiments.py --mode all
```

## Timeline
- [x] **10/8:** Check-In 1 - Simulation & GUI setup.
- [ ] **10/20-22:** Mid-Point Poster - 4 modes working, Pilot test complete.
- [ ] **11/10:** Check-In 2 - Complete all participant experiments, administer debriefs.
- [ ] **12/1-3:** Final Presentations - Data analysis and conclusion.
