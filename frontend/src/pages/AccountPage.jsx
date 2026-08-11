import { KeyRound, LogOut, TicketCheck } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { apiRequest } from '../api'
import { useAuth } from '../auth'
import Brand from '../components/Brand'
import FormField from '../components/FormField'
import StatusMessage from '../components/StatusMessage'
import SubmitButton from '../components/SubmitButton'
import { fieldError } from '../form'

export default function AccountPage() {
  const { logout, clearSession } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ old_password: '', new_password: '', confirmation: '' })
  const [error, setError] = useState(null)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setMessage('')
    if (form.new_password !== form.confirmation) {
      setError({ message: 'Пароли не совпадают.', localConfirmation: true })
      return
    }
    setLoading(true)
    try {
      await apiRequest('change-password', {
        method: 'POST',
        auth: true,
        body: JSON.stringify({ old_password: form.old_password, new_password: form.new_password }),
      })
      clearSession()
      navigate('/login', { replace: true, state: { message: 'Пароль изменен. Войдите заново.' } })
    } catch (requestError) {
      setError(requestError)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="account-page">
      <header className="account-header">
        <Brand />
        <button className="icon-text-button" type="button" onClick={handleLogout}><LogOut size={19} /> Выйти</button>
      </header>
      <main className="account-main">
        <section className="account-intro">
          <p className="eyebrow">Личный кабинет</p>
          <h1>Добро пожаловать в игру</h1>
          <p>Следующий шаг — заполнить профиль и зарегистрировать первый промокод.</p>
        </section>
        <section className="account-grid">
          <article className="account-placeholder">
            <span className="account-placeholder__icon"><TicketCheck size={26} /></span>
            <div><h2>Промокоды</h2><p>Раздел появится на следующем этапе разработки.</p></div>
          </article>
          <section className="password-panel">
            <div className="panel-heading"><KeyRound size={23} /><div><h2>Смена пароля</h2><p>После смены потребуется войти заново.</p></div></div>
            {message && <StatusMessage type="success">{message}</StatusMessage>}
            {error && !fieldError(error, 'old_password') && !fieldError(error, 'new_password') && !error.localConfirmation && <StatusMessage type="error">{error.message}</StatusMessage>}
            <form className="auth-form" onSubmit={handleSubmit}>
              <FormField id="old-password" label="Текущий пароль" type="password" autoComplete="current-password" value={form.old_password} error={fieldError(error, 'old_password')} onChange={(event) => setForm({ ...form, old_password: event.target.value })} required />
              <FormField id="account-new-password" label="Новый пароль" type="password" autoComplete="new-password" value={form.new_password} error={fieldError(error, 'new_password')} onChange={(event) => setForm({ ...form, new_password: event.target.value })} required />
              <FormField id="account-password-confirmation" label="Повторите новый пароль" type="password" autoComplete="new-password" value={form.confirmation} error={error?.localConfirmation ? error.message : ''} onChange={(event) => setForm({ ...form, confirmation: event.target.value })} required />
              <SubmitButton loading={loading}>Изменить пароль</SubmitButton>
            </form>
          </section>
        </section>
      </main>
    </div>
  )
}
