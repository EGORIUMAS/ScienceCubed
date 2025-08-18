const socket = io();

new Vue({
    el: '#app',
    data: {
        isLoggedIn: false,
        username: '',
        password: '',
        loginError: '',
        currentRound: null,
        initial_data: window.initial_data || { teams: [], currentQuestion: null },
        timer: 0,
        showingResults: false,
        correctAnswer: null
    },
    methods: {
        login() {
            fetch('/login', {
                method: 'POST',
                headers: {
                    'Authorization': 'Basic ' + btoa(this.username + ':' + this.password)
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.token) {
                    localStorage.setItem('token', data.token);
                    this.isLoggedIn = true;
                    this.loginError = '';
                } else {
                    this.loginError = data.message;
                }
            })
            .catch(error => {
                this.loginError = 'Ошибка входа: ' + error.message;
            });
        },
        selectRound(round) {
            this.currentRound = round;
        }
    },
    mounted() {
        console.log('Initial data:', this.initial_data);
        socket.on('new_question', (data) => {
            this.initial_data.currentQuestion = data;
            this.timer = data.time_limit;
            this.showingResults = false;
            this.correctAnswer = null;
            console.log('New question received:', data);
        });

        socket.on('timer_update', (data) => {
            this.timer = data.time;
        });

        socket.on('timer_end', () => {
            this.timer = 0;
        });

        socket.on('show_results', (data) => {
            this.correctAnswer = data.correct_answer;
            this.initial_data.teams = data.teams;
            this.showingResults = true;
            console.log('Results received:', data);
        });

        socket.on('round_ended', () => {
            this.initial_data.currentQuestion = null;
            this.timer = 0;
            this.showingResults = false;
            this.correctAnswer = null;
            console.log('Round ended');
        });
    }
});