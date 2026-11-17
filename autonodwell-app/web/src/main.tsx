import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { AppDataProvider } from './AppData'
import { AuthProvider } from './auth/AuthProvider'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <AppDataProvider>
        <App />
      </AppDataProvider>
    </AuthProvider>
  </StrictMode>,
)
