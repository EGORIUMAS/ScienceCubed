const socket = io();
let currentTime = 0;
let totalQuestions = 0;
let completedQuestions = 0;
let questionIds = [];
let timerInterval = null;
let questionCounter = 0; // For sequential question numbering
let currentRound = 1; // Track current round

const tickSound1 = document.getElementById('tick1-sound');
const tickSound2 = document.getElementById('tick2-sound');
const lastSound1 = document.getElementById('last1-sound');
const lastSound2 = document.getElementById('last2-sound');

const content = document.getElementById('content');
const waiting = document.getElementById('waiting');
const questionContainer = document.getElementById('question-container');
const resultsContainer = document.getElementById('results-container');
const questionText = document.getElementById('question-text');
const optionsDiv = document.getElementById('options');
const timerText = document.getElementById('timer-text');
const progressCircle = document.getElementById('progress-circle');
const timerSvg = document.getElementById('timer-svg');
const currentRoundElement = document.getElementById('current-round');
const questionProgress = document.getElementById('question-progress');
const correctAnswer = document.getElementById('correct-answer');
const leaderboardBody = document.querySelector('#leaderboard tbody');
const leaderboardHead = document.querySelector('#leaderboard thead tr');

// Show/hide sections with animation
function showSection(section) {
    [waiting, questionContainer, resultsContainer].forEach(el => el.classList.add('hidden'));
    content.style.opacity = 0;
    setTimeout(() => {
        section.classList.remove('hidden');
        content.style.opacity = 1;
    }, 500);
}

// Enable audio context for sound playback
function enableAudioContext() {
    // Create audio context if it doesn't exist and resume it
    if (!window.audioContextEnabled) {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
            const audioContext = new AudioContext();
            if (audioContext.state === 'suspended') {
                audioContext.resume();
            }
        }

        // Enable audio for all sound elements
        [tickSound1, tickSound2, lastSound1, lastSound2].forEach(audio => {
            if (audio) {
                audio.muted = false;
                audio.volume = 1.0;
            }
        });

        window.audioContextEnabled = true;
    }
}

// Initialize: show waiting
showSection(waiting);

// Clear any existing timer
function clearTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

// Start timer with proper sound sequence and fixed progress bar
function startTimer(duration) {
    clearTimer();
    currentTime = duration;
    let tickCounter = 0;

    const circumference = 2 * Math.PI * 140;
    progressCircle.style.strokeDasharray = circumference;
    // Start progress bar completely filled (will empty as time runs out)
    progressCircle.style.strokeDashoffset = 0;

    // Enable audio context on first user interaction
    enableAudioContext();

    updateTimerDisplay();

    timerInterval = setInterval(() => {
        currentTime--;
        updateTimerDisplay();

        if (currentTime > 0) {
            // Fixed sound timing: last2.mp3 plays at 2 seconds before end
            if (currentTime <= 4 && currentTime >= 3) {
                // 4-3 seconds remaining: play last1.mp3
                if (lastSound1) lastSound1.play();
                progressCircle.classList.add('pulse');
            } else if (currentTime <= 2 && currentTime > 0) {
                // 2-1 seconds remaining: play last2.mp3
                if (lastSound2) lastSound2.play();
                progressCircle.classList.add('pulse');
            } else {
                // Normal ticking: alternate between tick1 and tick2
                progressCircle.classList.remove('pulse');
                if (tickCounter % 2 === 0) {
                    if (tickSound1) tickSound1.play();
                } else {
                    if (tickSound2) tickSound2.play();
                }
                tickCounter++;
            }
        } else {
            // Timer ended
            clearTimer();
            timerText.textContent = '0';
            const circumference = 2 * Math.PI * 140;
            progressCircle.style.strokeDashoffset = circumference; // Completely empty
            timerSvg.classList.add('vibrate');
            setTimeout(() => timerSvg.classList.remove('vibrate'), 500);
            progressCircle.classList.remove('pulse');
        }
    }, 1000);
}

function updateTimerDisplay() {
    timerText.textContent = currentTime;
    const circumference = 2 * Math.PI * 140;
    const initialDuration = parseInt(timerText.getAttribute('data-initial') || currentTime);
    const progress = (currentTime - 1) / (initialDuration - 1);
    // Progress bar empties as time runs out (clockwise from top)
    const offset = circumference * progress;
    progressCircle.style.strokeDashoffset = offset;
}

socket.on('connect', () => {
    console.log('Socket connected, id=', socket.id);
});

// Log all incoming events
if (typeof socket.onAny === 'function') {
    socket.onAny((event, ...args) => {
        console.log('[onAny] event=', event, 'args=', args);
    });
}

socket.on('new_question', (data) => {
    console.log('Received new_question:', data);
    socket.emit('client_ready', { received: true, qid: data.id });

    clearTimer();
    showSection(questionContainer);
    questionText.textContent = data.text;
    currentRoundElement.textContent = data.round;
    currentRound = data.round; // Store current round
    optionsDiv.innerHTML = '';

    if (data.options) {
        const options = JSON.parse(data.options);
        for (let key in options) {
            const btn = document.createElement('div');
            btn.classList.add('option');
            btn.textContent = `${key}: ${options[key]}`;
            optionsDiv.appendChild(btn);
        }
    }

    questionCounter++;
    completedQuestions = questionCounter;

    // Calculate current question number based on round
    let displayQuestionNumber;
    if (currentRound >= 2) {
        // For rounds 2 and 3, show question relative to round start
        displayQuestionNumber = data.id - 10 * (currentRound - 1);
    } else {
        // For round 1, show sequential numbering
        displayQuestionNumber = completedQuestions;
    }

    // If server didn't send total_questions, estimate from data
    if (data.total_questions !== undefined) {
        totalQuestions = data.total_questions;
    }

    questionProgress.textContent = `${displayQuestionNumber}/${totalQuestions}`;
    questionIds.push(data.id);
    updateTableHeaders();

    // Store initial duration and start timer
    timerText.setAttribute('data-initial', data.time_limit);
    startTimer(data.time_limit);
});

socket.on('timer_update', (data) => {
    console.log('Received timer_update:', data);
    // We're handling timer locally now, but keep this for compatibility
});

socket.on('timer_end', () => {
    console.log('Received timer_end');
    clearTimer();
    currentTime = 0;
    timerText.textContent = '0';
    const circumference = 2 * Math.PI * 140;
    progressCircle.style.strokeDashoffset = circumference; // Completely empty
    timerSvg.classList.add('vibrate');
    setTimeout(() => timerSvg.classList.remove('vibrate'), 500);
    progressCircle.classList.remove('pulse');
});

socket.on('show_results', (data) => {
    console.log('Received show_results:', data);
    clearTimer();
    showSection(resultsContainer);

    // Only show correct answer if it's provided and not empty
    if (data.correct_answer && data.correct_answer.trim() !== '') {
        let displayAnswer = data.correct_answer;
        // Convert boolean values to Russian
        if (displayAnswer.toLowerCase() === 'true') {
            displayAnswer = 'правда';
        } else if (displayAnswer.toLowerCase() === 'false') {
            displayAnswer = 'ложь';
        }
        correctAnswer.textContent = `Правильный ответ: ${displayAnswer}`;
        correctAnswer.style.display = 'block';
    } else {
        correctAnswer.style.display = 'none';
    }

    leaderboardBody.innerHTML = '';
    // Sort by total score
    data.teams.sort((a, b) => b.score - a.score);
    data.teams.forEach((team, index) => {
        const row = document.createElement('tr');
        row.style.animation = `rowLift 0.5s ease-out ${index * 0.1}s forwards`;

        const nameCell = document.createElement('td');
        nameCell.textContent = team.name;
        row.appendChild(nameCell);

        // Scores for each question (from team.answers)
        const answers = JSON.parse(team.answers || '[]');
        questionIds.forEach((id, qIndex) => {
            const cell = document.createElement('td');
            const answer = answers.find(ans => ans.id === id);
            cell.textContent = answer ? answer.rate : 0;
            row.appendChild(cell);
        });

        const sumCell = document.createElement('td');
        sumCell.textContent = team.score;
        row.appendChild(sumCell);
        leaderboardBody.appendChild(row);
    });
});

socket.on('round_ended', () => {
    clearTimer();
    showSection(resultsContainer);
    // Reset for new round
    completedQuestions = 0;
    questionCounter = 0;
    questionIds = [];
    updateTableHeaders();
});

socket.on('game_info', (data) => {
    console.log('Received game_info:', data);
    if (data.total_questions !== undefined) {
        totalQuestions = data.total_questions;
        // Update display with current question number calculation
        let displayQuestionNumber;
        if (currentRound >= 2) {
            // This will be updated when we receive the actual question
            displayQuestionNumber = completedQuestions;
        } else {
            displayQuestionNumber = completedQuestions;
        }
        questionProgress.textContent = `${displayQuestionNumber}/${totalQuestions}`;
    }
});

socket.on('test_event', (data) => {
    console.log('Received test_event:', data);
});

// Function to update table headers (Question numbers and Summary symbol)
function updateTableHeaders() {
    // Clear all except Team and Sum
    while (leaderboardHead.children.length > 2) {
        leaderboardHead.removeChild(leaderboardHead.children[1]);
    }

    // Add question number headers
    questionIds.forEach((id, index) => {
        const th = document.createElement('th');
        // Calculate display question number based on round
        let displayQuestionNumber;
        if (currentRound >= 2) {
            displayQuestionNumber = id - 10 * (currentRound - 1);
        } else {
            displayQuestionNumber = index + 1;
        }
        th.textContent = `${displayQuestionNumber}`;
        leaderboardHead.insertBefore(th, leaderboardHead.lastChild);
    });
}