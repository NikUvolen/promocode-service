import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import { apiRequest } from '../api'
import { useAuth } from '../auth'
import AuthLayout from '../components/AuthLayout'
import FormField from '../components/FormField'
import StatusMessage from '../components/StatusMessage'
import SubmitButton from '../components/SubmitButton'
import { fieldError } from '../form'

export default function RegisterPage() {
  const { authenticated } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    email: '',
    password: '',
    confirm_password: '',
    personal_data_consent: false,
  })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  if (authenticated) return <Navigate to="/account" replace />

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await apiRequest('register', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      navigate(`/check-email?email=${encodeURIComponent(form.email)}`)
    } catch (requestError) {
      setError(requestError)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      eyebrow="Новый аккаунт"
      title="Регистрация"
      description="Создайте аккаунт, чтобы регистрировать промокоды."
    >
      {error && !fieldError(error, 'email') && !fieldError(error, 'password') && !fieldError(error, 'confirm_password') && !fieldError(error, 'personal_data_consent') && (
        <StatusMessage type="error">{error.message}</StatusMessage>
      )}
      <form className="auth-form" onSubmit={handleSubmit}>
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="name@example.com"
          value={form.email}
          error={fieldError(error, 'email')}
          onChange={(event) => setForm({ ...form, email: event.target.value })}
          required
        />
        <FormField
          id="confirm-password"
          label="Повторите пароль"
          type="password"
          autoComplete="new-password"
          placeholder="Введите пароль ещё раз"
          value={form.confirm_password}
          error={fieldError(error, 'confirm_password')}
          onChange={(event) => setForm({ ...form, confirm_password: event.target.value })}
          required
        />
        <FormField
          id="password"
          label="Пароль"
          type="password"
          autoComplete="new-password"
          placeholder="Не менее 8 символов"
          hint="Не используйте простой или полностью цифровой пароль."
          value={form.password}
          error={fieldError(error, 'password')}
          onChange={(event) => setForm({ ...form, password: event.target.value })}
          required
        />
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={form.personal_data_consent}
            onChange={(event) => setForm({ ...form, personal_data_consent: event.target.checked })}
          />
          <span className="checkbox-field__box" aria-hidden="true" />
          <span>Согласен на обработку персональных данных</span>
        </label>
        {fieldError(error, 'personal_data_consent') && (
          <span className="standalone-error">{fieldError(error, 'personal_data_consent')}</span>
        )}
        <SubmitButton loading={loading}>Создать аккаунт</SubmitButton>
      </form>
      <p className="auth-switch">
        Уже есть аккаунт? <Link to="/login">Войти</Link>
      </p>
    </AuthLayout>
  )
}
