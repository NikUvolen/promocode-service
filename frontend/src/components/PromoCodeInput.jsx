const CODE_LENGTH = 8

export function normalizePromoCode(value) {
  return value
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .slice(0, CODE_LENGTH)
}

export default function PromoCodeInput({ value, error, disabled, onChange }) {
  const characters = Array.from({ length: CODE_LENGTH }, (_, index) => (
    value[index] || ''
  ))

  return (
    <label className="promo-code-field">
      <span className="field__label">Промокод</span>
      <span className={`promo-code-control ${error ? 'promo-code-control--error' : ''}`}>
        <input
          className="promo-code-control__input"
          type="text"
          inputMode="text"
          autoCapitalize="characters"
          autoComplete="off"
          spellCheck="false"
          maxLength={CODE_LENGTH}
          value={value}
          disabled={disabled}
          aria-label="Промокод"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? 'promo-code-error' : undefined}
          onChange={(event) => onChange(normalizePromoCode(event.target.value))}
        />
        <span className="promo-code-slots" aria-hidden="true">
          {characters.map((character, index) => (
            <span className={`promo-code-slot ${character ? 'promo-code-slot--filled' : ''}`} key={index}>
              {character}
            </span>
          ))}
        </span>
      </span>
      {error && <span className="field__error" id="promo-code-error">{error}</span>}
    </label>
  )
}
