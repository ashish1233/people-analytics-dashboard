import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

// The ui-kit stylesheet must be imported once, before app styles, so the app
// can override a token if it ever needs to.
import '@insights-platform/ui-kit/styles.css';
import './global.css';

import { App } from './App';

const container = document.getElementById('root');
if (!container) throw new Error('Missing #root element in index.html');

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
