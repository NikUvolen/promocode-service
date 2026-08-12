import { Clock3, LockKeyhole, TicketCheck } from 'lucide-react'
import { useEffect, useState } from 'react'

import { promoApiRequest } from '../api'
import PromoCodeInput from './PromoCodeInput'
import StatusMessage from './StatusMessage'
import SubmitButton from './SubmitButton'

function formatDate(value) {
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'long',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatCountdown(seconds) {
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(rest).padStart(2, '0')}`
}

export default function PromoCodesPanel({ profileComplete }) {
  const [code, setCode] = useState('')
  const [codes, setCodes] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [blockedUntil, setBlockedUntil] = useState(null)
  const [remaining, setRemaining] = useState(0)

  useEffect(() => {
    let active = true
    Promise.all([
      promoApiRequest('', { auth: true }),
      promoApiRequest('registration-status', { auth: true }),
    ])
      .then(([data, registrationStatus]) => {
        if (!active) return
        setCodes(data.results)
        setTotal(data.count)
        if (registrationStatus.is_blocked) {
          setRemaining(registrationStatus.retry_after)
          setBlockedUntil(
            Date.now() + registrationStatus.retry_after * 1000,
          )
        }
      })
      .catch((requestError) => {
        if (active) setError(requestError.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!blockedUntil) return undefined

    function updateRemaining() {
      const nextRemaining = Math.max(
        0,
        Math.ceil((blockedUntil - Date.now()) / 1000),
      )
      setRemaining(nextRemaining)
      if (nextRemaining === 0) setBlockedUntil(null)
    }

    const interval = window.setInterval(updateRemaining, 1000)
    return () => window.clearInterval(interval)
  }, [blockedUntil])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setMessage('')

    if (code.length !== 8) {
      setError('Введите все 8 символов промокода.')
      return
    }

    setSubmitting(true)
    try {
      const registeredCode = await promoApiRequest('register', {
        method: 'POST',
        auth: true,
        body: JSON.stringify({ code }),
      })
      setCodes((current) => [registeredCode, ...current])
      setTotal((current) => current + 1)
      setCode('')
      setMessage(`Промокод ${registeredCode.code} зарегистрирован.`)
    } catch (requestError) {
      setError(requestError.message)
      if (requestError.payload?.reason === 'rate_limited') {
        const retryAfter = requestError.payload.retry_after
        setRemaining(retryAfter)
        setBlockedUntil(Date.now() + retryAfter * 1000)
      }
    } finally {
      setSubmitting(false)
    }
  }

  const isBlocked = remaining > 0
  const inputDisabled = !profileComplete || isBlocked

  return (
    <section className="promo-panel" aria-labelledby="promo-panel-title">
      <div className="promo-panel__header">
        <span className="promo-panel__icon"><TicketCheck size={27} /></span>
        <div>
          <p className="eyebrow">Участие в розыгрыше</p>
          <h2 id="promo-panel-title">Зарегистрировать промокод</h2>
          <p>Введите 8 символов с упаковки. Код попадет в ближайший розыгрыш.</p>
        </div>
        <span className="promo-panel__count">Кодов: {total}</span>
      </div>

      {!profileComplete && (
        <div className="promo-locked">
          <LockKeyhole size={20} />
          <span>Сначала заполните личные данные.</span>
          <a href="#profile">Перейти к профилю</a>
        </div>
      )}
      {isBlocked && (
        <div className="promo-ban" role="status">
          <Clock3 size={20} />
          <span>Ввод временно заблокирован</span>
          <strong>{formatCountdown(remaining)}</strong>
        </div>
      )}
      {message && <StatusMessage type="success">{message}</StatusMessage>}

      <form className="promo-entry" onSubmit={handleSubmit}>
        <PromoCodeInput
          value={code}
          error={error}
          disabled={inputDisabled}
          onChange={(value) => {
            setCode(value)
            setError('')
            setMessage('')
          }}
        />
        <SubmitButton loading={submitting} disabled={inputDisabled}>
          Зарегистрировать
        </SubmitButton>
      </form>

      <div className="promo-history">
        <h3>Мои промокоды</h3>
        {loading ? (
          <p className="promo-history__empty">Загружаем...</p>
        ) : codes.length === 0 ? (
          <p className="promo-history__empty">Зарегистрированных кодов пока нет.</p>
        ) : (
          <ul>
            {codes.map((item) => (
              <li key={item.code}>
                <span>{item.code}</span>
                <time dateTime={item.registered_at}>{formatDate(item.registered_at)}</time>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
