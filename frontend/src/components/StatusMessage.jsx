import { AlertCircle, CheckCircle2, Info } from 'lucide-react'

const icons = {
  error: AlertCircle,
  success: CheckCircle2,
  info: Info,
}

export default function StatusMessage({ type = 'info', children }) {
  const Icon = icons[type]
  return (
    <div className={`status status--${type}`} role={type === 'error' ? 'alert' : 'status'}>
      <Icon size={19} aria-hidden="true" />
      <span>{children}</span>
    </div>
  )
}
