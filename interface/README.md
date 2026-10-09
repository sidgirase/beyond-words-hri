# HRI User Study Web Interface

This directory contains the gamified, live-interaction web interface used for the CS7633 Human-Robot Interaction study. It is designed to act as a secure, blinding-compliant, and IRB-friendly Kiosk for evaluating the Hello Robot Stretch Series.

## How to Run

Because this app uses a lightweight Python backend, it is incredibly easy to run on any machine without needing Node.js or a complex build step.

### Windows (PowerShell)
```powershell
cd interface
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

### Mac / Linux
```bash
cd interface
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Once the server starts, open your browser to **http://localhost:5000**.

---

## Technical Specifications

* **Backend:** Python + Flask. Acts as a lightweight API to serve the web pages and append survey results to a local JSON database (`database.json`).
* **Frontend:** Vanilla HTML, Javascript, and CSS. 
* **Styling:** TailwindCSS (via CDN) for rapid, responsive UI development.
* **Speech-to-Text (STT):** Utilizes the native browser **Web Speech API** (`SpeechRecognition`). This entirely avoids the need for heavy background Whisper models by leveraging hardware-accelerated, built-in browser transcription. 
* **Data Storage:** Flat-file JSON structure. A `/api/submit` endpoint handles concurrent logging, while `/api/delete_user` allows Admins to scrub data.

---

## Evaluation Metrics (Likert Scales)

The study relies on carefully selected Likert scales to measure the subjective quality of the robot's clarification strategies. We incorporated established Human-Robot Interaction metrics rather than ad-hoc questions to ensure scientific validity:

1. **Perceived Intelligence (Godspeed Questionnaire Series)**
   * **Scale:** Semantic differential (e.g., Incompetent vs. Competent).
   * **Reasoning:** Ambiguity resolution is fundamentally a test of the robot's cognitive capabilities. The Godspeed scale (Bartneck et al., 2009) is the standard in HRI for measuring whether a robot's behavior makes it appear intelligent and sensible. We use this to test if a multimodal clarification strategy makes the robot seem more competent than a single-modality strategy.

2. **Trust in Automated Systems (Jian et al., 2000)**
   * **Scale:** 1 (Strongly Disagree) to 5 (Strongly Agree).
   * **Reasoning:** Trust is a primary factor in whether users will adopt robotic systems in their homes. We use modified trust constructs ("I am confident in the robot's ability to identify the correct object") to evaluate whether certain clarification strategies build or break user trust when errors occur.

3. **Clarification Effectiveness (Custom to this Study)**
   * **Scale:** 1 (Strongly Disagree) to 5 (Strongly Agree).
   * **Reasoning:** Since our specific independent variables are Audio vs. Gesture vs. Hybrid clarification, we needed questions specifically targeting the efficiency of the communication modality. We measure *Clarity* ("It was immediately clear what the robot was asking") to directly compare the cognitive load of audio versus physical gestures.

---

## Core Design Choices

To ensure a scientifically valid HRI study, several specific design choices were integrated into the architecture:

### 1. Kiosk Mode & Admin Security
The application is locked behind a Researcher Login screen (Password: `hri2026`). Users cannot accidentally start the study, nor can they exit the debriefing screen without the researcher resetting the app. Furthermore, a hidden Admin button exists in the corner during the study, allowing researchers to Pause the study, Restart it, or Delete the participant's data mid-run if they revoke consent.

### 2. Anonymity via UUIDs
To comply with standard IRB protocols for longitudinal (long-horizon) studies, no Personally Identifiable Information (PII) like names or emails are collected. When the Admin starts a new study, the system generates a random alphanumeric UUID (e.g., `user_8f2a`). If the user returns for a follow-up study, the researcher can simply type this UUID into the "Resume Past Participant" field to link their data anonymously.

### 3. Subject Blinding
The specific clarification mode (e.g., "Hybrid" or "Gesture Only") is strictly hidden from the participant's UI. The screen simply reads "Robot Interaction Trial." This single-blinding prevents expectation bias when users are filling out the Likert scales.

### 4. Within vs. Between Subjects
The Admin Dashboard allows the researcher to select the experimental design:
* **Within-Subjects:** The user will be routed through all 4 clarification modes sequentially.
* **Between-Subjects:** The researcher can explicitly lock the user into exactly one condition (Immediate, Audio, Gesture, or Hybrid).

### 5. "Test Run" Debugging Mode
To prevent polluting the `database.json` file with debug attempts during setup or demonstrations, researchers can use the Start Test Run button. This flags the session as `test_user`, and the Flask backend will automatically ignore any data submitted during that session.
