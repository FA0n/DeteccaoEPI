document.getElementById('login-form').addEventListener('submit', function(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    const validUsername = "Admin";
    const validPassword = "VisionSafe01";

    if (username === validUsername && password === validPassword) {
        window.location.href = 'dashboard.html';
    } else {
        document.getElementById('error-message').textContent = 'Usuário ou senha inválidos. Tente novamente.';
    }
});
