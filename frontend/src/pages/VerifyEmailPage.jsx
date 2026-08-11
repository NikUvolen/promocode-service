import { CheckCircle2, LoaderCircle, XCircle } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { apiRequest } from '../api'
import AuthLayout from '../components/AuthLayout'

export default function VerifyEmailPage() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const started = useRef(false)
  const [state, setState] = useState(
    token
      ? { status: 'loading', message: '' }
      : { status: 'error', message: 'В ссылке нет токена подтверждения.' },
  )

  useEffect(() => {
    if (started.current) return
    started.current = true
    if (!token) return

    apiRequest('verify-email', {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
      .then((result) => setState({ status: 'success', message: result.detail }))
      .catch((error) => setState({ status: 'error', message: error.message }))
  }, [token])

  const content = {
    loading: { icon: <LoaderCircle className="spin" size={32} />, title: 'Подтверждаем email' },
    success: { icon: <CheckCircle2 size={32} />, title: 'Email подтвержден' },
    error: { icon: <XCircle size={32} />, title: 'Ссылка не сработала' },
  }[state.status]

  return (
    <AuthLayout eyebrow="Подтверждение" title={content.title}>
      <div className={`result-icon result-icon--${state.status}`}>{content.icon}</div>
      {state.message && <p className="auth-description auth-description--result">{state.message}</p>}
      {state.status === 'success' && <Link className="button button--primary button--submit" to="/login">Войти</Link>}
      {state.status === 'error' && <Link className="button button--secondary button--submit" to="/register">Зарегистрироваться заново</Link>}
    </AuthLayout>
  )
}
