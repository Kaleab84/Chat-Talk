(() => {
  const form = document.getElementById('loginForm');
  const input = document.getElementById('username');
  const error = document.getElementById('loginError');
  if (!form || !input) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    error.textContent = '';
    const name = (input.value || '').trim().toLowerCase();
    if (!name) { error.textContent = 'Please enter a username.'; return; }
    switch (name) {
      case 'mark':
        location.href = '/ui/dashboard.html';
        break;
      case 'user':
        location.href = '/ui/chat.html';
        break;
      case 'devs':
        location.href = '/docs';
        break;
      default:
        error.textContent = 'Invalid username. Try mark, user, or devs.';
    }
  });
})();

