const socket = io();
let currentTime = 0;
let totalQuestions = 0;
let completedQuestions = 0;
let questionIds = [];
let timerInterval = null;
let questionCounter = 0; // For sequential question numbering
let currentRound = 1; // Track current round
let lastLeaderboardSnapshot = null;

const tickSound1 = document.getElementById('tick1-sound');
const tickSound2 = document.getElementById('tick2-sound');
const lastSound1 = document.getElementById('last1-sound');
const lastSound2 = document.getElementById('last2-sound');
const endSound = document.getElementById('end-sound')

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
const leaderboardHeadRow = document.getElementById('leaderboard-head-row');
const leaderboardBodyEl = document.getElementById('leaderboard-body');

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
            if (endSound) endSound.play();
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
/**
 * Parse team's answers into Map{id -> score}
 */
function parseAnswersMap(team) {
    try {
        const arr = typeof team.answers === 'string' ? JSON.parse(team.answers || '[]') : (team.answers || []);
        const map = new Map();
        arr.forEach(a => {
            if (a && (a.id !== undefined)) {
                // ensure numeric or string identity consistent
                map.set(String(a.id), Number(a.rate || 0));
            }
        });
        return map;
    } catch (e) {
        console.warn('Failed to parse team.answers', e);
        return new Map();
    }
}

/**
 * Build a deterministic ordered list of questionIds from server data.
 * Preference: if server provided data.question_ids, use it. Else union of all teams' answers sorted ascending.
 */
function extractQuestionIdsFromData(data) {
    if (Array.isArray(data.question_ids) && data.question_ids.length > 0) {
        return data.question_ids.map(String);
    }
    const idsSet = new Set();
    (data.teams || []).forEach(team => {
        const map = parseAnswersMap(team);
        for (let key of map.keys()) idsSet.add(key);
    });
    // sort numeric if possible
    const arr = Array.from(idsSet);
    arr.sort((a,b) => {
        const an = Number(a), bn = Number(b);
        if (!isNaN(an) && !isNaN(bn)) return an - bn;
        return a.localeCompare(b);
    });
    return arr;
}

/**
 * Create snapshot object from data
 */
function buildSnapshotFromData(data) {
    const qids = extractQuestionIdsFromData(data);
    const teams = (data.teams || []).map(team => {
        const answersMap = parseAnswersMap(team);
        // build per-question array in qids order
        const per = {};
        qids.forEach(id => { per[id] = Number(answersMap.get(id) || 0); });
        return {
            name: team.name,
            per,
            total: Number(team.score || Object.values(per).reduce((s,v)=>s+v,0))
        };
    });
    return { questionIds: qids, teams };
}

/**
 * Render snapshot to DOM (complete rebuild, no animation for new columns).
 * If `fast`==true — render without entrance animations (used when we first show old snapshot).
 */
function renderSnapshot(snapshot, fast = false) {
    // build header: Team | q... | Sum
    // clear header cells except first (Team) and sum (last) - but we will reconstruct entirely to be safe
    while (leaderboardHeadRow.firstChild) leaderboardHeadRow.removeChild(leaderboardHeadRow.firstChild);

    const thTeam = document.createElement('th');
    thTeam.textContent = 'Команда';
    leaderboardHeadRow.appendChild(thTeam);

    snapshot.questionIds.forEach(qid => {
        const th = document.createElement('th');
        th.dataset.qid = qid;
        th.textContent = displayQuestionNumber(qid);
        if (!fast) th.classList.add('col-new');
        leaderboardHeadRow.appendChild(th);
    });

    const thSum = document.createElement('th');
    thSum.classList.add('sum-header');
    thSum.textContent = 'Сумма';
    leaderboardHeadRow.appendChild(thSum);

    // body
    leaderboardBodyEl.innerHTML = '';
    snapshot.teams.forEach(team => {
        const tr = document.createElement('tr');
        tr.dataset.team = team.name;

        const tdName = document.createElement('td');
        tdName.textContent = team.name;
        tr.appendChild(tdName);

        snapshot.questionIds.forEach(qid => {
            const td = document.createElement('td');
            td.textContent = team.per[qid] || 0;
            tr.appendChild(td);
        });

        const tdSum = document.createElement('td');
        tdSum.classList.add('sum-cell');
        tdSum.textContent = team.total;
        tr.appendChild(tdSum);

        leaderboardBodyEl.appendChild(tr);
    });
}

/**
 * Helper: compute displayed question number (uses currentRound if set).
 * If qid is numeric and rounds have offsets (10 per round), compute like before.
 */
function displayQuestionNumber(qid) {
    // try to use currentRound (global variable) if set
    const idNum = Number(qid);
    if (!isNaN(idNum) && typeof currentRound === 'number' && currentRound >= 1) {
        if (currentRound >= 2) {
            return String(idNum - 10 * (currentRound - 1));
        } else {
            return String(idNum);
        }
    }
    return qid;
}

/**
 * Animate adding new question columns one-by-one.
 * newQids: array of qid strings that must be appended in order
 * newSnapshot: snapshot built from data (contains final totals)
 */
function animateAddColumns(newQids, newSnapshot, callback) {
    if (!newQids || newQids.length === 0) {
        if (callback) callback();
        return;
    }

    let idx = 0;

    function addNext() {
        if (idx >= newQids.length) {
            if (callback) callback();
            return;
        }
        const qid = newQids[idx];
        // append header th
        const th = document.createElement('th');
        th.dataset.qid = qid;
        th.textContent = displayQuestionNumber(qid);
        th.classList.add('col-new');
        // insert before sum header (which is last)
        const sumHeader = leaderboardHeadRow.querySelector('th.sum-header');
        leaderboardHeadRow.insertBefore(th, sumHeader);

        // for each row, append cell (with value from newSnapshot; if team didn't exist before, create)
        const rows = Array.from(leaderboardBodyEl.querySelectorAll('tr'));
        rows.forEach(tr => {
            const teamName = tr.dataset.team;
            const teamData = newSnapshot.teams.find(t => t.name === teamName);
            const score = teamData ? (teamData.per[qid] || 0) : 0;
            const td = document.createElement('td');
            td.textContent = score;
            td.classList.add('col-new','cell-highlight');
            tr.insertBefore(td, tr.querySelector('td.sum-cell')); // before sum cell
        });

        // For teams present in newSnapshot but not in DOM (new teams) — add new row
        newSnapshot.teams.forEach(team => {
            const exists = rows.some(r => r.dataset.team === team.name);
            if (!exists) {
                const trNew = document.createElement('tr');
                trNew.dataset.team = team.name;
                const tdName = document.createElement('td');
                tdName.textContent = team.name;
                trNew.appendChild(tdName);
                // for existing columns we must add empty/0 cells for previous qids
                const currentHeaderQids = Array.from(leaderboardHeadRow.querySelectorAll('th'))
                    .filter(th => th.dataset.qid)
                    .map(th => String(th.dataset.qid));
                currentHeaderQids.forEach(hqid => {
                    const td = document.createElement('td');
                    td.textContent = team.per[hqid] || 0;
                    trNew.appendChild(td);
                });
                const tdSum = document.createElement('td');
                tdSum.classList.add('sum-cell');
                tdSum.textContent = team.total;
                trNew.appendChild(tdSum);
                leaderboardBodyEl.appendChild(trNew);
            }
        });

        // animate sum updates for each row (increase by the newly added cell value)
        const trsAfter = Array.from(leaderboardBodyEl.querySelectorAll('tr'));
        trsAfter.forEach(tr => {
            const tName = tr.dataset.team;
            const domSumCell = tr.querySelector('td.sum-cell');
            const oldSum = Number(domSumCell ? domSumCell.textContent : 0);
            const teamNew = newSnapshot.teams.find(t => t.name === tName);
            const newSum = teamNew ? teamNew.total : oldSum;
            // animate number from oldSum to newSum over 400ms
            if (oldSum !== newSum) {
                animateNumber(domSumCell, oldSum, newSum, 400);
                domSumCell.classList.add('cell-highlight');
                setTimeout(() => domSumCell.classList.remove('cell-highlight'), 700);
            }
        });

        // small delay before adding next column so user sees sequence
        idx++;
        setTimeout(addNext, 450);
    }

    addNext();
}

/**
 * Animate numeric change in an element from `from` to `to` for `duration` ms.
 */
function animateNumber(el, from, to, duration) {
    if (!el) return;
    const start = performance.now();
    const diff = to - from;
    function step(now) {
        const t = Math.min(1, (now - start) / duration);
        const val = Math.round(from + diff * t);
        el.textContent = val;
        if (t < 1) requestAnimationFrame(step);
        else el.textContent = to;
    }
    requestAnimationFrame(step);
}

/**
 * Sort rows by new totals (from newSnapshot) with a visual reordering.
 */
function sortAndAnimate(newSnapshot, done) {
    const rows = Array.from(leaderboardBodyEl.querySelectorAll('tr'));
    // build map team->row
    const rowMap = new Map();
    rows.forEach(r => rowMap.set(r.dataset.team, r));

    // sort team list by total desc
    const sortedTeams = newSnapshot.teams.slice().sort((a,b) => b.total - a.total);

    // apply reordering: we'll append rows in sorted order with fade/transform
    leaderboardBodyEl.classList.add('reordering');

    // For visual smoothness, set fixed height to body container to avoid layout jump
    const bodyRect = leaderboardBodyEl.getBoundingClientRect();
    leaderboardBodyEl.style.minHeight = bodyRect.height + 'px';

    // animate: fade out slightly, then reorder DOM, then fade in
    rows.forEach(r => r.style.opacity = '0.6');

    setTimeout(() => {
        // reappend rows in sorted order
        sortedTeams.forEach(team => {
            const r = rowMap.get(team.name);
            if (r) leaderboardBodyEl.appendChild(r);
        });
        // restore opacity, let CSS transitions move them
        setTimeout(() => {
            const newRows = Array.from(leaderboardBodyEl.querySelectorAll('tr'));
            newRows.forEach(r => r.style.opacity = '1');
            // cleanup
            setTimeout(() => {
                leaderboardBodyEl.classList.remove('reordering');
                leaderboardBodyEl.style.minHeight = '';
                if (done) done();
            }, 450);
        }, 50);
    }, 250);
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
    console.log('Received show_results (leaderboard module):', data);
    clearTimer();
    showSection(resultsContainer);

    // Show correct answer if exists
    if (data.correct_answer && data.correct_answer.trim() !== '') {
        let displayAnswer = data.correct_answer;
        if (displayAnswer.toLowerCase() === 'true') displayAnswer = 'правда';
        else if (displayAnswer.toLowerCase() === 'false') displayAnswer = 'ложь';
        correctAnswer.textContent = `Правильный ответ: ${displayAnswer}`;
        correctAnswer.style.display = 'block';
    } else {
        correctAnswer.style.display = 'none';
    }

    // Build snapshot for new data
    const newSnapshot = buildSnapshotFromData(data);

    // If there was no previous snapshot -> render full
    if (!lastLeaderboardSnapshot) {
        renderSnapshot(newSnapshot, false);
        // store snapshot
        lastLeaderboardSnapshot = newSnapshot;
        // After initial render, do a final sort animation to ensure order is correct
        setTimeout(() => sortAndAnimate(newSnapshot), 200);
        return;
    }

    // If snapshots equal (same qids and same totals) — just re-render to ensure freshness
    const oldQids = lastLeaderboardSnapshot.questionIds.join(',');
    const newQidsStr = newSnapshot.questionIds.join(',');
    const totalsChanged = JSON.stringify(lastLeaderboardSnapshot.teams.map(t=>({n:t.name,s:t.total}))) !==
                          JSON.stringify(newSnapshot.teams.map(t=>({n:t.name,s:t.total})));

    // If question set identical but totals changed -> simply animate sum updates and sort
    if (oldQids === newQidsStr) {
        // update per-cell values (for safety) and animate sum changes
        const rows = Array.from(leaderboardBodyEl.querySelectorAll('tr'));
        rows.forEach(tr => {
            const tName = tr.dataset.team;
            const teamNew = newSnapshot.teams.find(t => t.name === tName);
            if (!teamNew) return;
            // update each per-question cell
            const qids = newSnapshot.questionIds;
            qids.forEach((qid, idx) => {
                const td = tr.children[1 + idx]; // 0: name, 1..n: qcells
                const newVal = teamNew.per[qid] || 0;
                if (td && Number(td.textContent) !== newVal) {
                    td.textContent = newVal;
                    td.classList.add('cell-highlight');
                    setTimeout(()=>td.classList.remove('cell-highlight'),700);
                }
            });
            // update sum
            const sumCell = tr.querySelector('td.sum-cell');
            if (sumCell) {
                const oldSum = Number(sumCell.textContent);
                const newSum = teamNew.total;
                if (oldSum !== newSum) {
                    animateNumber(sumCell, oldSum, newSum, 500);
                    sumCell.classList.add('cell-highlight');
                    setTimeout(()=>sumCell.classList.remove('cell-highlight'),700);
                }
            }
        });
        // finally sort
        setTimeout(()=> sortAndAnimate(newSnapshot), 300);
        lastLeaderboardSnapshot = newSnapshot;
        return;
    }

    // If question set differs -> determine new questions (append order)
    const addedQids = newSnapshot.questionIds.filter(q => !lastLeaderboardSnapshot.questionIds.includes(q));
    // Render previous snapshot first (fast, without animation) if current DOM doesn't match it
    renderSnapshot(lastLeaderboardSnapshot, true);

    // Now animate adding the new columns sequentially, then sort
    animateAddColumns(addedQids, newSnapshot, () => {
        // Final sort animation
        sortAndAnimate(newSnapshot, () => {
            // finally store snapshot
            lastLeaderboardSnapshot = newSnapshot;
        });
    });
});

socket.on('round_ended', () => {
    clearTimer();
    showSection(resultsContainer);
    // Reset snapshot and clear DOM table (keeps headers minimal)
    lastLeaderboardSnapshot = null;
    // rebuild empty header (Team | Sum)
    while (leaderboardHeadRow.firstChild) leaderboardHeadRow.removeChild(leaderboardHeadRow.firstChild);
    const thTeam = document.createElement('th');
    thTeam.textContent = 'Команда';
    leaderboardHeadRow.appendChild(thTeam);
    const thSum = document.createElement('th');
    thSum.classList.add('sum-header');
    thSum.textContent = 'Сумма';
    leaderboardHeadRow.appendChild(thSum);
    leaderboardBodyEl.innerHTML = '';
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