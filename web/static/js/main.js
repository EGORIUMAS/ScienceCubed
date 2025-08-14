new Vue({
    el: '#app',
    data: {
        isLoggedIn: false,
        username: '',
        password: '',
        loginError: '',
        currentRound: 1,
        currentQuestion: window.initialData ? window.initialData.currentQuestion : null,
        timer: 0,
        showingResults: false,
        teams: window.initialData ? window.initialData.teams : [],
        teamResults: [],
        socket: null,
        token: null,
        questions: []
    },
    created() {
        this.socket = io();
        this.setupSocketListeners();
    },
    methods: {
        async login() {
            try {
                this.loginError = '';  // Сбрасываем ошибку
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Basic ' + btoa(this.username + ':' + this.password)
                    }
                });

                const data = await response.json();

                if (!response.ok) {
                    this.loginError = data.message || 'Ошибка входа';
                    console.error('Login failed:', data.message);
                    return;
                }

                if (data.token) {
                    this.token = data.token;
                    this.isLoggedIn = true;
                    this.loadQuestions();
                } else {
                    this.loginError = 'Неверный ответ сервера';
                }
            } catch (error) {
                console.error('Login error:', error);
                this.loginError = 'Ошибка при попытке входа';
            }
        },

        async loadQuestions() {
            try {
                const response = await fetch('/api/questions', {
                    headers: {
                        'Authorization': this.token
                    }
                });
                this.questions = await response.json();
            } catch (error) {
                console.error('Failed to load questions:', error);
            }
        },

        selectRound(round) {
            this.currentRound = round;
            this.currentQuestion = this.questions.find(q => q.round === round);
        },

        startQuestion() {
            if (this.currentQuestion) {
                this.socket.emit('start_question', {
                    question_id: this.currentQuestion.id
                });
                this.startTimer();
            }
        },

        startTimer() {
            this.timer = 30; // время в секундах
            const timerInterval = setInterval(() => {
                this.timer--;
                this.socket.emit('timer_update', { time: this.timer });

                if (this.timer <= 0) {
                    clearInterval(timerInterval);
                }
            }, 1000);
        },

        showAnswers() {
            this.socket.emit('show_answers', {
                question_id: this.currentQuestion.id
            });
        },

        setupSocketListeners() {
            this.socket.on('results_update', (data) => {
                this.teamResults = data.results;
                this.showingResults = true;
            });
        }
    }
});