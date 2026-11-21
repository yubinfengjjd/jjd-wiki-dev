import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { installButtonMotion } from './buttonMotion';
import './styles.css';
import './apple-theme.css';

installButtonMotion();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
