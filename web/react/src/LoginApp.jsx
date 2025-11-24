import { useState } from 'react';
import { getGreeting } from './utils/displayName.js';

const roleRoutes = {
  admin: '/ui/admin.html',
  user: '/ui/chat.html',
  dev: '/ui/dev.html',
};

export default function LoginApp() {
  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [error, setError] = useState('');
  const [greeting] = useState(() => getGreeting());

  const submit = (event) => {
    event.preventDefault();
    const trimmedRole = role.trim().toLowerCase();
    const trimmedName = name.trim();
    if (!trimmedRole) {
      setError('Please enter a role (admin, user, dev).');
      return;
    }
    if (!trimmedName) {
      setError('Please enter your name.');
      return;
    }
    const destination = roleRoutes[trimmedRole];
    if (!destination) {
      setError('Invalid role. Try admin, user, or dev.');
      return;
    }
    try {
      window.localStorage.setItem('displayName', trimmedName);
    } catch {}
    window.location.href = destination;
  };

  return (
    <div className='react-app'>
      <header className='container header react-header'>
        <div className='brand'>CFC Technologies</div>
        <div className='greet'>{greeting ? `Hi, ${greeting}!` : 'Welcome back'}</div>
      </header>
      <main className='container login-container'>
        <section className='panel active login-panel' id='login'>
          <h2>Welcome</h2>
          <p>Enter your first name and role to continue.</p>
          <form className='stack' onSubmit={submit}>
            <input
              type='text'
              placeholder='Your name'
              autoComplete='off'
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
            <input
              type='text'
              placeholder='Your role (admin | user | dev)'
              autoComplete='off'
              value={role}
              onChange={(event) => setRole(event.target.value)}
              required
            />
            <button className='btn' type='submit' aria-label='Login'>
              Login
            </button>
          </form>
          {error ? (
            <div className='meta' style={{ marginTop: '10px', color: '#c0564a' }}>
              {error}
            </div>
          ) : null}
        </section>
      </main>
      <footer className='container footer'></footer>
    </div>
  );
}
