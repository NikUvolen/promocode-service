import { createContext, useContext, useMemo, useState } from 'react'

import {
  apiRequest,
  clearTokens,
  getTokens,
  saveTokens,
} from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [authenticated, setAuthenticated] = useState(() => Boolean(getTokens()))

  const value = useMemo(
    () => ({
      authenticated,
      async login(credentials) {
        const tokens = await apiRequest('login', {
          method: 'POST',
          body: JSON.stringify(credentials),
        })
        saveTokens(tokens)
        setAuthenticated(true)
      },
      async logout() {
        const refresh = getTokens()?.refresh
        try {
          if (refresh) {
            await apiRequest('logout', {
              method: 'POST',
              body: JSON.stringify({ refresh }),
            })
          }
        } finally {
          clearTokens()
          setAuthenticated(false)
        }
      },
      clearSession() {
        clearTokens()
        setAuthenticated(false)
      },
    }),
    [authenticated],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
