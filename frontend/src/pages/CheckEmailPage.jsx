import { MailCheck } from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { apiRequest } from '../api'
import AuthLayout from '../components/AuthLayout'
import StatusMessage from '../components/StatusMessage'

export default function CheckEmailPage() {
  const [params] = useSearchParams()
  const email = params.get('email') || ''
  const [state, setState] = useState({ loading: false, message: '', error: '' })

  async function resend() {
    if (!email) return
    setState({ loading: true, message: '', error: '' })
    try {
      const result = await apiRequest('resend-verification', {
        method: 'POST',
        body: JSON.stringify({ email }),
      })
      setState({ loading: false, message: result.detail, error: '' })
    } catch (error) {
      setState({ loading: false, message: '', error: error.message })
    }
  }

  return (
    <AuthLayout eyebrow="Почти готово" title="Проверьте почту">
      <div className="result-icon"><MailCheck size={30} /></div>
      <p className="auth-description auth-description--result">
        Отправили ссылку для подтверждения{email ? <> на <strong>{email}</strong></> : ''}.
      </p>
      {state.message && <StatusMessage type="success">{state.message}</StatusMessage>}
      {state.error && <StatusMessage type="error">{state.error}</StatusMessage>}
      <button className="button button--secondary button--submit" disabled={!email || state.loading} onClick={resend} type="button">
        {state.loading ? 'Отправляем...' : 'Отправить еще раз'}
      </button>
      <p className="auth-switch"><Link to="/login">Вернуться ко входу</Link></p>
    </AuthLayout>
  )
}
