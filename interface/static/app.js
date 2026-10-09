const ADMIN_PASS = "hri2026"; // Hardcoded for local study

let scenarios = [
    'Immediate (No Clarification)', 
    'Audio Only', 
    'Gesture Only', 
    'Hybrid (Audio + Gesture)'
];

let currentTrialIndex = 0;
let sessionData = {
    user: {
        uuid: null,
        studyType: null
    },
    trials: []
};

let trialStartTime = null;
let currentTrialData = {};

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
    document.getElementById(`screen-${screenId}`).classList.remove('hidden');
    
    // Show floating admin button only if user is in-study
    if(screenId !== 'admin-login' && screenId !== 'admin-dashboard') {
        document.getElementById('admin-float-btn').classList.remove('hidden');
    } else {
        document.getElementById('admin-float-btn').classList.add('hidden');
    }
}

// --- ADMIN LOGIC ---
function loginAdmin() {
    if(document.getElementById('admin-pass').value === ADMIN_PASS) {
        showScreen('admin-dashboard');
    } else {
        alert("Incorrect Password");
    }
}

function generateUUID() {
    return 'user_' + Math.random().toString(36).substr(2, 6);
}

function setupNewUser() {
    const type = document.getElementById('admin-study-type').value;
    sessionData.user.uuid = generateUUID();
    sessionData.user.studyType = type;
    alert(`New Participant Ready!\n\nWrite down this UUID for long-term tracking: ${sessionData.user.uuid}\n\nPlease hand the device to the user.`);
    showScreen('onboarding');
}

function resumeUser() {
    const uuid = document.getElementById('admin-resume-uuid').value;
    if(!uuid) { alert("Enter a valid UUID"); return; }
    sessionData.user.uuid = uuid;
    sessionData.user.studyType = "within"; // Default for resumed
    alert(`Resuming Participant: ${uuid}\n\nPlease hand the device to the user.`);
    showScreen('onboarding');
}

function openAdminModal() { document.getElementById('admin-modal').classList.remove('hidden'); }
function closeAdminModal() { 
    document.getElementById('admin-modal').classList.add('hidden');
    document.getElementById('admin-modal-actions').classList.add('hidden');
    document.getElementById('modal-unlock-btn').classList.remove('hidden');
    document.getElementById('modal-admin-pass').value = '';
}

function unlockAdminModal() {
    if(document.getElementById('modal-admin-pass').value === ADMIN_PASS) {
        document.getElementById('admin-modal-actions').classList.remove('hidden');
        document.getElementById('modal-unlock-btn').classList.add('hidden');
    } else {
        alert("Incorrect Password");
    }
}

function pauseStudy() {
    alert("Study Paused. The screen is locked until the admin clicks OK.");
}

function restartStudy() {
    if(confirm("Are you sure you want to restart this participant's session? All unsaved current progress will be lost.")) {
        closeAdminModal();
        currentTrialIndex = 0;
        showScreen('onboarding');
    }
}

async function deleteParticipant() {
    if(confirm("WARNING: This will permanently delete ALL data for this UUID from the database. Proceed?")) {
        try {
            await fetch('/api/delete_user', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ uuid: sessionData.user.uuid })
            });
            alert("Participant Data Deleted.");
            closeAdminModal();
            window.location.reload(); // Reset whole app back to Admin Login
        } catch(e) {
            console.error(e);
            alert("Failed to delete.");
        }
    }
}

// --- SPEECH TO TEXT LOGIC ---
let recognition = null;
let isRecording = false;

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onstart = function() {
        isRecording = true;
        const micBtn = document.getElementById('mic-btn');
        micBtn.classList.remove('bg-red-500', 'hover:bg-red-600');
        micBtn.classList.add('bg-green-500', 'hover:bg-green-600', 'animate-pulse');
        micBtn.innerText = '🔴 Listening...';
    };

    recognition.onresult = function(event) {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            transcript += event.results[i][0].transcript;
        }
        document.getElementById('command-input').value = transcript;
    };

    recognition.onerror = function(event) {
        console.error("Speech Recognition Error: ", event.error);
        stopRecordingUI();
    };

    recognition.onend = function() {
        stopRecordingUI();
    };
} else {
    console.warn("Web Speech API is not supported in this browser.");
}

function stopRecordingUI() {
    isRecording = false;
    const micBtn = document.getElementById('mic-btn');
    micBtn.classList.remove('bg-green-500', 'hover:bg-green-600', 'animate-pulse');
    micBtn.classList.add('bg-red-500', 'hover:bg-red-600');
    micBtn.innerText = '🎤 Speak';
}

function toggleSpeechRecognition() {
    if (!recognition) {
        alert("Speech Recognition is not supported in your current browser. Please use Google Chrome or Microsoft Edge.");
        return;
    }
    
    if (isRecording) {
        recognition.stop();
    } else {
        document.getElementById('command-input').value = '';
        recognition.start();
    }
}

// --- TUTORIAL LOGIC ---
function startTutorial() {
    const age = document.getElementById('user-age').value;
    if(!age) { alert("Please enter your age."); return; }
    sessionData.user.age = age;
    showScreen('tutorial');
}

let testMediaRecorder;
let testAudioChunks = [];

async function recordTestAudio() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        testMediaRecorder = new MediaRecorder(stream);
        const btn = document.getElementById('tutorial-record-btn');
        const player = document.getElementById('tutorial-audio-player');
        
        testMediaRecorder.ondataavailable = e => { testAudioChunks.push(e.data); };
        
        testMediaRecorder.onstop = () => {
            const audioBlob = new Blob(testAudioChunks, { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(audioBlob);
            player.src = audioUrl;
            player.classList.remove('hidden');
            btn.innerText = "🔴 Record Test Audio (3s)";
            btn.classList.remove('bg-green-500');
            btn.classList.add('bg-red-500');
            testAudioChunks = [];
        };

        testMediaRecorder.start();
        btn.innerText = "Listening...";
        btn.classList.remove('bg-red-500');
        btn.classList.add('bg-green-500');
        
        // Record for 3 seconds then stop
        setTimeout(() => {
            if(testMediaRecorder.state === "recording") testMediaRecorder.stop();
        }, 3000);
        
    } catch (err) {
        alert("Microphone access denied or unavailable.");
        console.error(err);
    }
}

function skipTutorial() { startTrials(); }
function finishTutorial() { startTrials(); }

// --- USER LOGIC ---
function startTrials() {
    // Admin Study Type Logic applied
    if (sessionData.user.studyType === 'between-immediate') {
        scenarios = ['Immediate (No Clarification)'];
    } else if (sessionData.user.studyType === 'between-audio') {
        scenarios = ['Audio Only'];
    } else if (sessionData.user.studyType === 'between-gesture') {
        scenarios = ['Gesture Only'];
    } else if (sessionData.user.studyType === 'between-hybrid') {
        scenarios = ['Hybrid (Audio + Gesture)'];
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
