import { useState } from 'react'
import { Link } from 'react-router-dom'

import { apiRequest } from '../api'
import AuthLayout from '../components/AuthLayout'
import FormField from '../components/FormField'
import StatusMessage from '../components/StatusMessage'
import SubmitButton from '../components/SubmitButton'
import { fieldError } from '../form'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setMessage('')
    try {
      const result = await apiRequest('password-reset', {
        method: 'POST',
        body: JSON.stringify({ email }),
      })
      setMessage(result.detail)
    } catch (requestError) {
      setError(requestError)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout eyebrow="Восстановление" title="Забыли пароль?" description="Укажите email аккаунта — отправим ссылку для смены пароля.">
      {message && <StatusMessage type="success">{message}</StatusMessage>}
      {error && !fieldError(error, 'email') && <StatusMessage type="error">{error.message}</StatusMessage>}
      <form className="auth-form" onSubmit={handleSubmit}>
        <FormField id="reset-email" label="Email" type="email" autoComplete="email" placeholder="name@example.com" value={email} error={fieldError(error, 'email')} onChange={(event) => setEmail(event.target.value)} required />
        <SubmitButton loading={loading}>Отправить ссылку</SubmitButton>
      </form>
      <p className="auth-switch"><Link to="/login">Вернуться ко входу</Link></p>
    </AuthLayout>
  )
}
