import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth'
import AuthLayout from '../components/AuthLayout'
import FormField from '../components/FormField'
import StatusMessage from '../components/StatusMessage'
import SubmitButton from '../components/SubmitButton'
import { fieldError } from '../form'

export default function LoginPage() {
  const { authenticated, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  if (authenticated) return <Navigate to="/account" replace />

  async function handleSubmit(event) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await login(form)
      navigate('/account')
    } catch (requestError) {
      setError(requestError)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout eyebrow="Личный кабинет" title="Войти">
      {location.state?.message && (
        <StatusMessage type="success">{location.state.message}</StatusMessage>
      )}
      {error && !fieldError(error, 'email') && !fieldError(error, 'password') && (
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
          id="password"
          label="Пароль"
          type="password"
          autoComplete="current-password"
          placeholder="Введите пароль"
          value={form.password}
          error={fieldError(error, 'password')}
          onChange={(event) => setForm({ ...form, password: event.target.value })}
          required
        />
        <Link className="form-link form-link--right" to="/forgot-password">
          Не помню пароль
        </Link>
        <SubmitButton loading={loading}>Войти</SubmitButton>
      </form>
      <p className="auth-switch">
        Еще нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
      </p>
    </AuthLayout>
  )
}
