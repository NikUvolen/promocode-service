function nationalDigits(value) {
  const rawValue = String(value || '')
  let digits = rawValue.replace(/\D/g, '')
  if (rawValue.trim().startsWith('+7')) {
    digits = digits.slice(1)
  } else if (
    digits.length > 10
    && (digits.startsWith('7') || digits.startsWith('8'))
  ) {
    digits = digits.slice(1)
  }
  return digits.slice(0, 10)
}

function formatNationalPhone(digits) {
  if (!digits) return ''

  let result = `(${digits.slice(0, 3)}`
  if (digits.length >= 3) result += ')'
  if (digits.length > 3) result += ` ${digits.slice(3, 6)}`
  if (digits.length > 6) result += `-${digits.slice(6, 8)}`
  if (digits.length > 8) result += `-${digits.slice(8, 10)}`
  return result
}

export function isCompleteRussianPhone(value) {
  return nationalDigits(value).length === 10
}

export default function PhoneField({ id, label, value, error, onChange }) {
  const digits = nationalDigits(value)
  const formattedValue = formatNationalPhone(digits)
  const errorId = error ? `${id}-error` : undefined

  function handleChange(event) {
    const nextDigits = nationalDigits(event.target.value)
    const nextValue = nextDigits
      ? `+7 ${formatNationalPhone(nextDigits)}`
      : ''
    onChange(nextValue)
  }

  return (
    <label className="field" htmlFor={id}>
      <span className="field__label">{label}</span>
      <span className={`phone-control ${error ? 'phone-control--error' : ''}`}>
        <span className="phone-control__prefix" aria-hidden="true">+7</span>
        <input
          id={id}
          type="tel"
          inputMode="numeric"
          autoComplete="tel-national"
          placeholder="(999) 123-45-67"
          value={formattedValue}
          maxLength={15}
          aria-invalid={Boolean(error)}
          aria-describedby={errorId}
          onChange={handleChange}
          required
        />
      </span>
      {error && <span className="field__error" id={errorId}>{error}</span>}
    </label>
  )
}
