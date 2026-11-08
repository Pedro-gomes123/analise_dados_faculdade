// Token de acesso (DEC-013). Sem refresh token no MVP: expirou, volta ao login.
const TOKEN_KEY = 'vigia.token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage bloqueado: não há token para apagar.
  }
}
