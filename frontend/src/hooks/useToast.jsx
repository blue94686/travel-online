import { createContext, useCallback, useContext, useReducer } from 'react'

const ToastContext = createContext(null)

function toastReducer(state, action) {
  switch (action.type) {
    case 'ADD':
      return [...state, { id: Date.now(), ...action.payload }]
    case 'REMOVE':
      return state.filter(t => t.id !== action.payload)
    default:
      return state
  }
}

export function ToastProvider({ children }) {
  const [toasts, dispatch] = useReducer(toastReducer, [])

  const addToast = useCallback((message, type = 'info', duration = 3000) => {
    const id = Date.now()
    dispatch({ type: 'ADD', payload: { message, type } })
    if (duration > 0) {
      setTimeout(() => dispatch({ type: 'REMOVE', payload: id }), duration)
    }
  }, [])

  const removeToast = useCallback((id) => {
    dispatch({ type: 'REMOVE', payload: id })
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) return { toasts: [], addToast: () => {}, removeToast: () => {} }
  return ctx
}
