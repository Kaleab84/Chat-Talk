import { useEffect, useState } from 'react';
import { getGreeting } from './utils/displayName.js';

export default function DocsApp() {
  const [greeting, setGreeting] = useState(() => getGreeting());

  useEffect(() => {
    setGreeting(getGreeting());
  }, []);

  return (
    <div className='react-app'>
      <header className='container header react-header'>
        <div className='brand'>CFC Software Support</div>
        <div className='greet'>{greeting ? `Hi, ${greeting}!` : 'Welcome back'}</div>
      </header>

      <main className='container docs-layout docs-container'>
        <section className='panel active docs-panel'>
          <div className='panel-body'>
            <h2>API Documentation</h2>
            <p>Explore FastAPI docs without leaving the UI.</p>
            <iframe
              className='docs-frame'
              title='FastAPI Docs'
              src='/docs'
              loading='lazy'
              referrerPolicy='no-referrer'
            />
          </div>
        </section>
      </main>

      <footer className='container footer'>
        <a className='btn' href='/ui/login.html' aria-label='Back to Login'>
          Back to Login
        </a>
      </footer>
    </div>
  );
}
