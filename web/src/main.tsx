import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Toaster } from 'sonner'

import App from './App.tsx'
import './index.css'
import { CaseProvider } from './state/case-store.tsx'

const root = document.getElementById('root')
if (!root) throw new Error('Root element #root is missing from index.html')

createRoot(root).render(
  <StrictMode>
    <CaseProvider>
      <App />
      <Toaster theme="dark" position="bottom-right" richColors closeButton />
    </CaseProvider>
  </StrictMode>,
)
