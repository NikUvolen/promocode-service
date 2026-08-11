import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import { apiRequest } from '../api'
import AuthLayout from '../components/AuthLayout'
import FormField from '../components/FormField'
import StatusMessage from '../components/StatusMessage'
import SubmitButton from '../components/SubmitButton'
import { fieldError } from '../form'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const uid = params.get('uid')
  const token = params.get('token')
  const [passwords, setPasswords] = useState({ password: '', confirmation: '' })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    if (passwords.password !== passwords.confirmation) {
      setError({ message: 'Пароли не совпадают.', localConfirmation: true })
      return
    }
    setLoading(true)
    try {
      await apiRequest('password-reset-confirm', {
        method: 'POST',
        body: JSON.stringify({ uid, token, new_password: passwords.password }),
      })
      navigate('/login', { replace: true, state: { message: 'Пароль изменен. Теперь можно войти.' } })
    } catch (requestError) {
      setError(requestError)
    } finally {
      setLoading(false)
    }
  }

  const invalidLink = !uid || !token

  return (
    <AuthLayout eyebrow="Новый пароль" title="Сменить пароль">
      {invalidLink && <StatusMessage type="error">В ссылке не хватает данных для восстановления.</StatusMessage>}
      {error && !fieldError(error, 'new_password') && !error.localConfirmation && <StatusMessage type="error">{error.message}</StatusMessage>}
      <form className="auth-form" onSubmit={handleSubmit}>
        <FormField id="new-password" label="Новый пароль" type="password" autoComplete="new-password" placeholder="Не менее 8 символов" value={passwords.password} error={fieldError(error, 'new_password')} onChange={(event) => setPasswords({ ...passwords, password: event.target.value })} required />
        <FormField id="new-password-confirmation" label="Повторите пароль" type="password" autoComplete="new-password" placeholder="Еще раз новый пароль" value={passwords.confirmation} error={error?.localConfirmation ? error.message : ''} onChange={(event) => setPasswords({ ...passwords, confirmation: event.target.value })} required />
        <SubmitButton loading={loading} disabled={invalidLink}>Сохранить пароль</SubmitButton>
      </form>
    </AuthLayout>
  )
}
