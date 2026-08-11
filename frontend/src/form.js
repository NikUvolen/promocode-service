export function fieldError(error, field) {
  const value = error?.payload?.[field]
  if (Array.isArray(value)) return String(value[0])
  if (typeof value === 'string') return value
  return ''
}
