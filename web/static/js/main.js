const socket = io();
let currentTime = 0;
let totalQuestions = 0; // Будет обновляться
let completedQuestions = 0;
let questionIds = []; // Для заголовков в таблице (ID вопросов)

const tickSound = document.getElementById('tick-sound');
const lastTickSound = document.getElementById('last-tick-sound');
const endSound = document.getElementById('end-sound');

const content = document.getElementById('content');
const waiting = document.getElementById('waiting');
const questionContainer = document.getElementById('question-container');
const resultsContainer = document.getElementById('results-container');
const questionText = document.getElementById('question-text');
const optionsDiv = document.getElementById('options');
const timerText = document.getElementById('timer-text');
const progressCircle = document.getElementById('progress-circle');
const timerSvg = document.getElementById('timer-svg');
const currentRound = document.getElementById('current-round');
const questionProgress = document.getElementById('question-progress');
const correctAnswer = document.getElementById('correct-answer');
const leaderboardBody = document.querySelector('#leaderboard tbody');
const leaderboardHead = document.querySelector('#leaderboard thead tr');

// Показать/скрыть секции с анимацией
function showSection(section) {
    [waiting, questionContainer, resultsContainer].forEach(el => el.classList.add('hidden'));
    content.style.opacity = 0;
    setTimeout(() => {
        section.classList.remove('hidden');
        content.style.opacity = 1;
    }, 500);
}

// Инициализация: показываем ожидание
showSection(waiting);

socket.on('new_question', (data) => {
    showSection(questionContainer);
    questionText.textContent = data.text;
    currentRound.textContent = data.round;
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
    currentTime = data.time_limit;
    timerText.textContent = currentTime;
    const circumference = 2 * Math.PI * 90; // Для r=90
    progressCircle.style.strokeDasharray = circumference;
    progressCircle.style.strokeDashoffset = 0;
    completedQuestions++;
    questionProgress.textContent = `${completedQuestions}/${totalQuestions}`;
    questionIds.push(data.id); // Добавляем ID вопроса для таблицы
    // Обновляем заголовки таблицы динамически
    updateTableHeaders();
});

socket.on('timer_update', (data) => {
    currentTime = data.time;
    timerText.textContent = currentTime;
    const circumference = 2 * Math.PI * 90;
    const offset = circumference * (1 - currentTime / (parseInt(timerText.textContent) || 30));
    progressCircle.style.strokeDashoffset = offset;

    if (currentTime <= 4 && currentTime > 0) {  // Учёт 4 секунд, как в вашем файле
        progressCircle.classList.add('pulse');
        lastTickSound.play();  // Играет весь файл для urgency
    } else if (currentTime > 0) {
        tickSound.play();  // Стандартное тиканье
    }
});

socket.on('timer_end', () => {
    endSound.play();  // Играет весь end.mp3
    timerSvg.classList.add('vibrate');
    setTimeout(() => timerSvg.classList.remove('vibrate'), 500);
    progressCircle.classList.remove('pulse');
});

socket.on('show_results', (data) => {
    showSection(resultsContainer);
    correctAnswer.textContent = `Правильный ответ: ${data.correct_answer}`;
    leaderboardBody.innerHTML = '';
    // Сортировка по суммарному баллу
    data.teams.sort((a, b) => b.score - a.score);
    data.teams.forEach((team, index) => {
        const row = document.createElement('tr');
        row.style.animation = `rowLift 0.5s ease-out ${index * 0.1}s forwards`; // Эффект взлёта
        const nameCell = document.createElement('td');
        nameCell.textContent = team.name;
        row.appendChild(nameCell);

        // Баллы за каждый вопрос (из team.answers)
        const answers = JSON.parse(team.answers || '[]');
        questionIds.forEach(id => {
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
    // Показываем результаты и сбрасываем прогресс
    showSection(resultsContainer);
    completedQuestions = 0;
    questionIds = [];
    updateTableHeaders();
});

socket.on('game_info', (data) => {
    if (data.total_questions !== undefined) {
        totalQuestions = data.total_questions;
        questionProgress.textContent = `${completedQuestions}/${totalQuestions}`;
    }
});

// Функция для обновления заголовков таблицы (Балл за вопрос ID)
function updateTableHeaders() {
    // Очищаем кроме Команда и Сумма
    while (leaderboardHead.children.length > 2) {
        leaderboardHead.removeChild(leaderboardHead.children[1]);
    }
    questionIds.forEach(id => {
        const th = document.createElement('th');
        th.textContent = `Q${id}`;
        leaderboardHead.insertBefore(th, leaderboardHead.lastChild);
    });
}

// При подключении запросим текущее состояние (опционально)
// socket.emit('get_current_state'); // Если добавите на сервере