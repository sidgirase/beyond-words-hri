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

### Target 1: Check-In 1 (10/8)
**Focus:** Foundation systems setup.
- **P1 (Simulation & VLA):** Finalize VLA deployment on the simulation-based robot.
- **P2 (Interface):** Build the gamified chat/audio GUI for human-robot interaction.
- **P3 (Metrics):** Design and implement the initial scoring metric.

### Target 2: Mid-Point Poster (10/20-22)
**Focus:** Have the 4 modes functioning in simulation and complete the pilot test.
- **P1 (Simulation & VLA):** Implement the 4 clarification modes (Immediate, Ask, Gesture, Hybrid) in MuJoCo.
- **P2 (Interface):** Set up data logging for objective (time, success) and subjective metrics.
- **P3 (Metrics & Pilot):** Conduct the pilot test to verify ambiguity/urgency holds before the main study.

### Target 3: Check-In 2 (11/10)
**Focus:** Main user study on the physical robot.
- **P1 (Physical Robot):** Translate the 4 clarification modes from simulation to the physical Stretch 2/3 robot.
- **P2 (User Study Execution):** Conduct the main participant experiments across the four conditions.
- **P3 (Physical Translation):** Ensure simulated gestures translate properly to physical Stretch limits.

### Target 4: Final Presentations (12/1-3)
**Focus:** Data analysis and final conclusions.
- **P1 (Physical Robot):** Support any final mechanical/robotic verifications needed for reporting.
- **P2 (User Study Execution):** Administer final "Score Debrief" surveys and finalize participant records.
- **P3 (Data Analysis & Conclusion):** Statistically analyze objective scores vs. survey ratings and determine best mode.

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

### Local Setup & Utility Commands
If running locally on a dedicated machine, ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

You can run the starter scripts for each subsystem as follows:

**1. Simulation (P1)**
```bash
python simulation/run_mujoco_experiments.py --mode all
```

**2. Interface (P2)**
```bash
python interface/start_gui.py
```

**3. Data Analysis (P3)**
```bash
python data_analysis/pilot_scoring.py
```

## Timeline
- [x] **10/8:** Check-In 1 - Simulation & GUI setup.
- [ ] **10/20-22:** Mid-Point Poster - 4 modes working, Pilot test complete.
- [ ] **11/10:** Check-In 2 - Complete all participant experiments, administer debriefs.
- [ ] **12/1-3:** Final Presentations - Data analysis and conclusion.
