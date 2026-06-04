import { Outlet } from 'react-router-dom'
import { AuthProvider } from './hooks/useAuth.jsx'
import { ToastProvider } from './hooks/useToast.jsx'
import ToastContainer from './components/common/Toast.jsx'

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Outlet />
        <ToastContainer />
      </ToastProvider>
    </AuthProvider>
  )
}
