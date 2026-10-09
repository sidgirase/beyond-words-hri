const scenarios = [
    'Assume Mode', 
    'Audio Only (Yes)', 
    'Audio Only (No)', 
    'Gesture Only (Yes)', 
    'Gesture Only (No)', 
    'Hybrid (Yes)', 
    'Hybrid (No)'
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
    const exp = document.getElementById('user-exp').value;
    
    if(!age) { alert("Please enter your age."); return; }

    sessionData.user = { age, robotExperience: exp };
    
    // Shuffle scenarios for counterbalancing (optional, keeping linear for now)
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

function replayAction() {
    // This would eventually send a WebSockets/ROS signal to the physical robot!
    console.log("Replaying robot action...");
    alert("Replay signal sent to robot!");
    currentTrialData.interactionLogs.push({action: "replay_clicked", time: Date.now()});
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
