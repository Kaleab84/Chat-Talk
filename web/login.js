(() => {
  const form = document.getElementById('loginForm');
  const roleInput = document.getElementById('role');
  const nameInput = document.getElementById('name');
  const error = document.getElementById('loginError');
  if (!form || !roleInput || !nameInput) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    error.textContent = '';
    const role = (roleInput.value || '').trim().toLowerCase();
    const displayName = (nameInput.value || '').trim();
    if (!role) { error.textContent = 'Please enter a role (admin, user, dev).'; return; }
    if (!displayName) { error.textContent = 'Please enter your name.'; return; }

    try { localStorage.setItem('displayName', displayName); } catch {}

    switch (role) {
      case 'admin':
        location.href = '/ui/dashboard.html';
        break;
      case 'user':
        location.href = '/ui/chat.html';
        break;
      case 'dev':
        // Use wrapper page so it has Back to Login and greeting
        location.href = '/ui/docs.html';
        break;
      default:
        error.textContent = 'Invalid role. Try admin, user, or dev.';
    }
  });
})();

