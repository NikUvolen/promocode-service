import { createContext, useContext, useEffect, useMemo, useState } from 'react'

import {
  apiRequest,
  clearLegacyTokenStorage,
  clearSession as notifySessionCleared,
  onSessionCleared,
} from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [authenticated, setAuthenticated] = useState(false)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let active = true
    clearLegacyTokenStorage()
    const unsubscribe = onSessionCleared(() => setAuthenticated(false))

    apiRequest('session', { auth: true })
      .then((session) => {
        if (active) setAuthenticated(session.authenticated)
      })
      .catch(() => {
        if (active) setAuthenticated(false)
      })
      .finally(() => {
        if (active) setReady(true)
      })

    return () => {
      active = false
      unsubscribe()
    }
  }, [])

  const value = useMemo(
    () => ({
      authenticated,
      ready,
      async login(credentials) {
        await apiRequest('login', {
          method: 'POST',
          body: JSON.stringify(credentials),
        })
        setAuthenticated(true)
      },
      async logout() {
        try {
          await apiRequest('logout', { method: 'POST' })
        } finally {
          notifySessionCleared()
          setAuthenticated(false)
        }
      },
      clearSession() {
        notifySessionCleared()
        setAuthenticated(false)
      },
    }),
    [authenticated, ready],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
