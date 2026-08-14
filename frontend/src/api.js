const API_ROOT = '/api/v1'
const SESSION_CLEARED_EVENT = 'gear-drop:session-cleared'
let refreshPromise = null

export class ApiError extends Error {
  constructor(payload, status) {
    super(firstMessage(payload) || 'Не удалось выполнить запрос.')
    this.name = 'ApiError'
    this.payload = payload
    this.status = status
  }
}

function firstMessage(value) {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return firstMessage(value[0])
  if (value && typeof value === 'object') {
    if (value.detail) return firstMessage(value.detail)
    return firstMessage(Object.values(value)[0])
  }
  return ''
}

export function clearSession() {
  window.dispatchEvent(new Event(SESSION_CLEARED_EVENT))
}

export function clearLegacyTokenStorage() {
  localStorage.removeItem('gear-drop.tokens')
}

function getCookie(name) {
  const prefix = `${encodeURIComponent(name)}=`
  const cookie = document.cookie
    .split('; ')
    .find((item) => item.startsWith(prefix))
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : ''
}

async function parseResponse(response) {
  if (response.status === 204) return null
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) return null
  return response.json()
}

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise

  refreshPromise = performTokenRefresh()
  try {
    return await refreshPromise
  } finally {
    refreshPromise = null
  }
}

async function performTokenRefresh() {
  const response = await fetch(`${API_ROOT}/auth/refresh/`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
  })

  if (!response.ok) {
    clearSession()
    return false
  }

  return true
}

export function onSessionCleared(listener) {
  window.addEventListener(SESSION_CLEARED_EVENT, listener)
  return () => window.removeEventListener(SESSION_CLEARED_EVENT, listener)
}

async function request(endpoint, options = {}) {
  const { auth = false, retry = true, ...fetchOptions } = options
  const headers = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  }

  const method = (fetchOptions.method || 'GET').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    headers['X-CSRFToken'] = getCookie('csrftoken')
  }

  const [path, query] = endpoint.split('?')
  const url = `${API_ROOT}/${path}/${query ? `?${query}` : ''}`
  const response = await fetch(url, {
    ...fetchOptions,
    headers,
    credentials: 'same-origin',
  })

  if (response.status === 401 && auth && retry) {
    const refreshed = await refreshAccessToken()
    if (refreshed) return request(endpoint, { ...options, retry: false })
  }

  const payload = await parseResponse(response)
  if (!response.ok) throw new ApiError(payload, response.status)
  return payload
}

export function apiRequest(path, options = {}) {
  return request(`auth/${path}`, options)
}

export function promoApiRequest(path = '', options = {}) {
  const suffix = path
    ? `${path.startsWith('?') ? '' : '/'}${path}`
    : ''
  return request(`promo-codes${suffix}`, options)
}

export function drawsApiRequest(options = {}) {
  return request('draws', options)
}
