import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource-variable/archivo/wdth.css';
import '@fontsource/noto-serif-sc/600.css';
import { App } from './App';
import './backdrop/instance';
import { installButtonMotion } from './buttonMotion';
import './styles.css';

installButtonMotion();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
