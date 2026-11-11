document.addEventListener('DOMContentLoaded', () => {
    // 1. Alternância de visibilidade da senha (olhinho)
    const toggleButtons = document.querySelectorAll('.toggle-password');

    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const inputField = document.getElementById(targetId);

            if (inputField.type === 'password') {
                inputField.type = 'text';
                this.textContent = '🙈';
            } else {
                inputField.type = 'password';
                this.textContent = '👁️';
            }
        });
    });

    // 2. Validação do formulário de cadastro antes do POST
    const registerForm = document.getElementById('register-form');
    
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            const errorText = document.getElementById('password-error');

            if (password.length < 8) {
                e.preventDefault();
                errorText.textContent = 'A senha deve conter no mínimo 8 caracteres.';
                return;
            }

            if (password !== confirmPassword) {
                e.preventDefault();
                errorText.textContent = 'As senhas não coincidem. Tente novamente.';
                return;
            }

            errorText.textContent = ''; // Limpa o erro se tudo estiver válido
        });
    }
});