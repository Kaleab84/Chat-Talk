import React from 'react';
import ReactDOM from 'react-dom/client';
import LoginApp from './LoginApp.jsx';
import './react-dashboard.css';
import '../../styles.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <LoginApp />
  </React.StrictMode>
);
