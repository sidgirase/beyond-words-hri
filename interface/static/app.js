let scenarios = [
    'Immediate (No Clarification)', 
    'Audio Only', 
    'Gesture Only', 
    'Hybrid (Audio + Gesture)'
];

let currentTrialIndex = 0;
let sessionData = {
    user: {},
    trials: []
};

let trialStartTime = null;
let currentTrialData = {};

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
    document.getElementById(`screen-${screenId}`).classList.remove('hidden');
}

function startTrials() {
    const age = document.getElementById('user-age').value;
    const studyType = document.getElementById('study-type').value;
    
    if(!age) { alert("Please enter your age."); return; }

    sessionData.user = { age, studyType };
    
    // Admin Study Type Logic
    if (studyType === 'between') {
        // Pick one random mode
        const randomMode = scenarios[Math.floor(Math.random() * scenarios.length)];
        scenarios = [randomMode];
    }
    
    document.getElementById('trial-total').innerText = scenarios.length;
    currentTrialIndex = 0;
    loadTrial();
}

function loadTrial() {
    if (currentTrialIndex >= scenarios.length) {
        showScreen('debrief');
        return;
    }

    const scenario = scenarios[currentTrialIndex];
    document.getElementById('scenario-name').innerText = scenario;
    document.getElementById('trial-counter').innerText = currentTrialIndex + 1;
    
    // Reset trial data
    currentTrialData = {
        scenario: scenario,
        interactionLogs: []
    };
    trialStartTime = Date.now();
    
    showScreen('trial');
}

function endTrial(isSuccess) {
    const durationSec = (Date.now() - trialStartTime) / 1000.0;
    currentTrialData.success = isSuccess;
    currentTrialData.duration_seconds = durationSec;
    
    // Move to evaluation
    showScreen('evaluation');
}

async function replayAction() {
    // End the current trial with 'retried' status and save it
    const durationSec = (Date.now() - trialStartTime) / 1000.0;
    currentTrialData.success = "retried";
    currentTrialData.duration_seconds = durationSec;
    currentTrialData.evaluation = "none (retried)";
    
    sessionData.trials.push(currentTrialData);
    
    // Send to backend
    try {
        await fetch('/api/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user: sessionData.user,
                trial_index: currentTrialIndex,
                data: currentTrialData
            })
        });
    } catch(e) {
        console.error("Failed to save to backend:", e);
    }
    
    alert("Replay signal sent to robot! Restarting this trial iteration.");
    // Restart the current trial without advancing the index
    loadTrial();
}

async function submitEval(event) {
    event.preventDefault();
    const form = document.getElementById('eval-form');
    const formData = new FormData(form);
    
    const evalResults = {};
    formData.forEach((value, key) => { evalResults[key] = value; });
    
    currentTrialData.evaluation = evalResults;
    sessionData.trials.push(currentTrialData);
    
    // Send to backend immediately to prevent data loss
    try {
        await fetch('/api/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user: sessionData.user,
                trial_index: currentTrialIndex,
                data: currentTrialData
            })
        });
    } catch(e) {
        console.error("Failed to save to backend:", e);
    }
    
    form.reset();
    currentTrialIndex++;
    loadTrial();
}
