import { CheckCircle2, KeyRound, LogOut, Mail, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { apiRequest } from '../api'
import { useAuth } from '../auth'
import Brand from '../components/Brand'
import FormField from '../components/FormField'
import PhoneField, { isCompleteRussianPhone } from '../components/PhoneField'
import PromoCodesPanel from '../components/PromoCodesPanel'
import StatusMessage from '../components/StatusMessage'
import SubmitButton from '../components/SubmitButton'
import { fieldError } from '../form'

export default function AccountPage() {
  const { logout, clearSession } = useAuth()
  const navigate = useNavigate()
  const [profile, setProfile] = useState({
    email: '',
    first_name: '',
    last_name: '',
    middle_name: '',
    no_middle_name: false,
    phone: '',
    is_complete: false,
  })
  const [profileState, setProfileState] = useState({
    loading: true,
    saving: false,
    error: null,
    message: '',
  })
  const [passwordForm, setPasswordForm] = useState({
    old_password: '',
    new_password: '',
    confirmation: '',
  })
  const [passwordError, setPasswordError] = useState(null)
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [notificationSettings, setNotificationSettings] = useState({
    promo_code_email_notifications: true,
  })
  const [notificationState, setNotificationState] = useState({
    loading: true,
    saving: false,
    error: null,
    message: '',
  })

  useEffect(() => {
    let active = true

    apiRequest('profile', { auth: true })
      .then((data) => {
        if (active) {
          setProfile(data)
          setProfileState((current) => ({ ...current, loading: false }))
        }
      })
      .catch((requestError) => {
        if (!active) return
        if (requestError.status === 401) {
          clearSession()
          navigate('/login', { replace: true })
          return
        }
        setProfileState((current) => ({
          ...current,
          loading: false,
          error: requestError,
        }))
      })

    apiRequest('notification-settings', { auth: true })
      .then((data) => {
        if (!active) return
        setNotificationSettings(data)
        setNotificationState((current) => ({ ...current, loading: false }))
      })
      .catch((requestError) => {
        if (!active) return
        if (requestError.status === 401) {
          clearSession()
          navigate('/login', { replace: true })
          return
        }
        setNotificationState((current) => ({
          ...current,
          loading: false,
          error: requestError,
        }))
      })

    return () => {
      active = false
    }
  }, [clearSession, navigate])

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  async function handleProfileSubmit(event) {
    event.preventDefault()
    if (!isCompleteRussianPhone(profile.phone)) {
      setProfileState((current) => ({
        ...current,
        error: {
          message: 'Введите номер полностью.',
          payload: { phone: 'Введите 10 цифр номера телефона.' },
        },
        message: '',
      }))
      return
    }
    setProfileState((current) => ({
      ...current,
      saving: true,
      error: null,
      message: '',
    }))
    try {
      const updatedProfile = await apiRequest('profile', {
        method: 'PATCH',
        auth: true,
        body: JSON.stringify({
          first_name: profile.first_name,
          last_name: profile.last_name,
          middle_name: profile.middle_name,
          no_middle_name: profile.no_middle_name,
          phone: profile.phone,
        }),
      })
      setProfile(updatedProfile)
      setProfileState({
        loading: false,
        saving: false,
        error: null,
        message: 'Данные профиля сохранены.',
      })
    } catch (requestError) {
      setProfileState((current) => ({
        ...current,
        saving: false,
        error: requestError,
      }))
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault()
    setPasswordError(null)
    if (passwordForm.new_password !== passwordForm.confirmation) {
      setPasswordError({ message: 'Пароли не совпадают.', localConfirmation: true })
      return
    }
    setPasswordLoading(true)
    try {
      await apiRequest('change-password', {
        method: 'POST',
        auth: true,
        body: JSON.stringify({
          old_password: passwordForm.old_password,
          new_password: passwordForm.new_password,
        }),
      })
      clearSession()
      navigate('/login', { replace: true, state: { message: 'Пароль изменен. Войдите заново.' } })
    } catch (requestError) {
      setPasswordError(requestError)
    } finally {
      setPasswordLoading(false)
    }
  }

  async function handleNotificationChange(event) {
    const enabled = event.target.checked
    setNotificationState({
      loading: false,
      saving: true,
      error: null,
      message: '',
    })
    try {
      const updatedSettings = await apiRequest('notification-settings', {
        method: 'PATCH',
        auth: true,
        body: JSON.stringify({
          promo_code_email_notifications: enabled,
        }),
      })
      setNotificationSettings(updatedSettings)
      setNotificationState({
        loading: false,
        saving: false,
        error: null,
        message: 'Настройка сохранена.',
      })
    } catch (requestError) {
      setNotificationState({
        loading: false,
        saving: false,
        error: requestError,
        message: '',
      })
    }
  }

  function updateProfile(field, value) {
    setProfile((current) => ({ ...current, [field]: value }))
    setProfileState((current) => ({ ...current, error: null, message: '' }))
  }

  return (
    <div className="account-page">
      <header className="account-header">
        <div className="account-header__inner">
          <Brand />
          <button className="icon-text-button" type="button" onClick={handleLogout}><LogOut size={19} /> Выйти</button>
        </div>
      </header>
      <main className="account-main">
        <section className="account-intro">
          <p className="eyebrow">Личный кабинет</p>
          <h1>Личный кабинет</h1>
          <p>Регистрируйте промокоды и следите за своим участием.</p>
        </section>
        {!profileState.loading && <PromoCodesPanel profileComplete={profile.is_complete} />}
        <section className="account-grid">
          <section className="profile-panel" id="profile">
            <div className="panel-heading profile-panel__heading">
              <UserRound size={23} />
              <div>
                <h2>Личные данные</h2>
                <p>{profile.is_complete ? 'Профиль заполнен' : 'Заполните все обязательные поля'}</p>
              </div>
              {profile.is_complete && <CheckCircle2 className="profile-complete-icon" size={22} aria-label="Профиль заполнен" />}
            </div>

            {profileState.loading ? (
              <div className="profile-loading" role="status">Загружаем данные...</div>
            ) : (
              <form className="profile-form" onSubmit={handleProfileSubmit}>
                {profileState.message && <StatusMessage type="success">{profileState.message}</StatusMessage>}
                {profileState.error && !['first_name', 'last_name', 'middle_name', 'phone'].some((field) => fieldError(profileState.error, field)) && (
                  <StatusMessage type="error">{profileState.error.message}</StatusMessage>
                )}
                <FormField id="profile-email" label="Email" type="email" value={profile.email} disabled />
                <div className="profile-form__row">
                  <FormField id="last-name" label="Фамилия" autoComplete="family-name" maxLength={100} value={profile.last_name} error={fieldError(profileState.error, 'last_name')} onChange={(event) => updateProfile('last_name', event.target.value)} required />
                  <FormField id="first-name" label="Имя" autoComplete="given-name" maxLength={100} value={profile.first_name} error={fieldError(profileState.error, 'first_name')} onChange={(event) => updateProfile('first_name', event.target.value)} required />
                </div>
                <FormField id="middle-name" label="Отчество" autoComplete="additional-name" maxLength={100} value={profile.middle_name} error={fieldError(profileState.error, 'middle_name')} disabled={profile.no_middle_name} onChange={(event) => updateProfile('middle_name', event.target.value)} required={!profile.no_middle_name} />
                <label className="checkbox-field profile-checkbox">
                  <input
                    type="checkbox"
                    checked={profile.no_middle_name}
                    onChange={(event) => {
                      updateProfile('no_middle_name', event.target.checked)
                      if (event.target.checked) updateProfile('middle_name', '')
                    }}
                  />
                  <span className="checkbox-field__box" aria-hidden="true" />
                  <span>Нет отчества</span>
                </label>
                <PhoneField id="phone" label="Телефон" value={profile.phone} error={fieldError(profileState.error, 'phone')} onChange={(value) => updateProfile('phone', value)} />
                <SubmitButton loading={profileState.saving}>Сохранить профиль</SubmitButton>
              </form>
            )}
          </section>

          <aside className="account-sidebar">
            <section className="settings-panel">
              <div className="panel-heading"><Mail size={23} /><div><h2>Уведомления</h2><p>Управляйте необязательными письмами.</p></div></div>
              {notificationState.error && <StatusMessage type="error">{notificationState.error.message}</StatusMessage>}
              {notificationState.message && <StatusMessage type="success">{notificationState.message}</StatusMessage>}
              <label className="notification-setting">
                <span>
                  <strong>Регистрация промокода</strong>
                  <small>Отправлять письмо после успешного добавления кода.</small>
                </span>
                <span className="switch-field">
                  <input
                    type="checkbox"
                    role="switch"
                    aria-label="Письма о регистрации промокода"
                    checked={notificationSettings.promo_code_email_notifications}
                    disabled={notificationState.loading || notificationState.saving}
                    onChange={handleNotificationChange}
                  />
                  <span className="switch-field__track" aria-hidden="true" />
                </span>
              </label>
              <p className="settings-panel__note">Письмо о выигрыше отправляется всегда.</p>
            </section>
            <section className="password-panel">
              <div className="panel-heading"><KeyRound size={23} /><div><h2>Смена пароля</h2><p>После смены потребуется войти заново.</p></div></div>
              {passwordError && !fieldError(passwordError, 'old_password') && !fieldError(passwordError, 'new_password') && !passwordError.localConfirmation && <StatusMessage type="error">{passwordError.message}</StatusMessage>}
              <form className="auth-form" onSubmit={handlePasswordSubmit}>
                <FormField id="old-password" label="Текущий пароль" type="password" autoComplete="current-password" value={passwordForm.old_password} error={fieldError(passwordError, 'old_password')} onChange={(event) => setPasswordForm({ ...passwordForm, old_password: event.target.value })} required />
                <FormField id="account-new-password" label="Новый пароль" type="password" autoComplete="new-password" value={passwordForm.new_password} error={fieldError(passwordError, 'new_password')} onChange={(event) => setPasswordForm({ ...passwordForm, new_password: event.target.value })} required />
                <FormField id="account-password-confirmation" label="Повторите новый пароль" type="password" autoComplete="new-password" value={passwordForm.confirmation} error={passwordError?.localConfirmation ? passwordError.message : ''} onChange={(event) => setPasswordForm({ ...passwordForm, confirmation: event.target.value })} required />
                <SubmitButton loading={passwordLoading}>Изменить пароль</SubmitButton>
              </form>
            </section>
          </aside>
        </section>
      </main>
    </div>
  )
}
