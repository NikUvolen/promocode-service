import { Eye, EyeOff } from 'lucide-react'
import { useState } from 'react'

export default function FormField({
  label,
  id,
  type = 'text',
  error,
  hint,
  ...inputProps
}) {
  const [visible, setVisible] = useState(false)
  const isPassword = type === 'password'
  const inputType = isPassword && visible ? 'text' : type
  const describedBy = [error ? `${id}-error` : '', hint ? `${id}-hint` : '']
    .filter(Boolean)
    .join(' ')

  return (
    <label className="field" htmlFor={id}>
      <span className="field__label">{label}</span>
      <span className={`field__control ${error ? 'field__control--error' : ''}`}>
        <input
          id={id}
          type={inputType}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy || undefined}
          {...inputProps}
        />
        {isPassword && (
          <button
            className="field__toggle"
            type="button"
            onClick={() => setVisible((current) => !current)}
            aria-label={visible ? 'Скрыть пароль' : 'Показать пароль'}
            title={visible ? 'Скрыть пароль' : 'Показать пароль'}
          >
            {visible ? <EyeOff size={19} /> : <Eye size={19} />}
          </button>
        )}
      </span>
      {error && (
        <span className="field__error" id={`${id}-error`}>
          {error}
        </span>
      )}
      {hint && !error && (
        <span className="field__hint" id={`${id}-hint`}>
          {hint}
        </span>
      )}
    </label>
  )
}
