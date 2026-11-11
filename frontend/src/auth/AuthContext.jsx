import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { auth } from '../api/index.js'
import { getToken, setToken } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(getToken()))

  useEffect(() => {
    if (!getToken()) return
    auth
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  // login/register grąžina { token, user }
  const signIn = useCallback(({ token, user }) => {
    setToken(token)
    setUser(user)
  }, [])

  const signOut = useCallback(async () => {
    await auth.logout().catch(() => {})
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
