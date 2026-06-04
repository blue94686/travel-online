import { X, CheckCircle2, AlertCircle, Info, AlertTriangle } from 'lucide-react'
import { useToast } from '../../hooks/useToast.jsx'
import './Toast.css'

const ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

export default function ToastContainer() {
  const { toasts, removeToast } = useToast()

  return (
    <div className="toast-container">
      {toasts.map(toast => {
        const Icon = ICONS[toast.type] || Info
        return (
          <div className={`toast toast-${toast.type || 'info'}`} key={toast.id}>
            <Icon size={16} />
            <span>{toast.message}</span>
            <button onClick={() => removeToast(toast.id)}><X size={14} /></button>
          </div>
        )
      })}
    </div>
  )
}
