export const authBase = process.env.NEXT_PUBLIC_AUTH_BASE_URL || 'https://api.sovable.ai'

type AuthResponse = {
  access_token?: string
  refresh_token?: string
  token_type?: string
  expires_in?: number
  dev_code?: string
  delivery?: string
  user?: { id: string; display_name?: string; email?: string; role?: string }
  detail?: string
}

async function request(path: string, init: RequestInit = {}): Promise<AuthResponse> {
  const response = await fetch(`${authBase}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init.headers || {}) },
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || `Authentication request failed (${response.status})`)
  }
  return payload
}

export async function startVerification(
  channel: 'email' | 'phone',
  destination: string,
  purpose: 'registration' | 'login' = 'login',
  account_type: 'user' | 'admin' | 'creator' = 'user',
) {
  return request(`/auth/register/${channel}/start`, {
    method: 'POST',
    body: JSON.stringify({ destination, purpose, account_type }),
  })
}

export async function startEmailActivation(
  email: string,
  displayName: string,
  accountType: 'user' | 'admin' | 'creator' = 'user',
) {
  return request('/auth/email/activation/start', {
    method: 'POST',
    body: JSON.stringify({ email, display_name: displayName, account_type: accountType }),
  })
}

export async function completeEmailActivation(token: string) {
  const result = await request('/auth/email/activation/complete', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
  if (result.access_token) {
    window.localStorage.setItem('solvable_session_token', result.access_token)
  }
  if (result.refresh_token) {
    window.localStorage.setItem('solvable_refresh_token', result.refresh_token)
  }
  return result
}

export async function verifyVerification(
  channel: 'email' | 'phone',
  destination: string,
  code: string,
  purpose: 'registration' | 'login',
  display_name?: string,
  account_type: 'user' | 'admin' | 'creator' = 'user',
) {
  const result = await request(`/auth/register/${channel}/verify`, {
    method: 'POST',
    body: JSON.stringify({ destination, code, purpose, display_name, account_type }),
  })
  if (result.access_token) {
    window.localStorage.setItem('solvable_session_token', result.access_token)
  }
  if (result.refresh_token) {
    window.localStorage.setItem('solvable_refresh_token', result.refresh_token)
  }
  return result
}

export async function getCurrentUser() {
  const token = window.localStorage.getItem('solvable_session_token')
  if (!token) return null
  const response = await fetch(`${authBase}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) return null
  return response.json()
}

export async function logout() {
  const refresh_token = window.localStorage.getItem('solvable_refresh_token')
  await request('/auth/logout', {
    method: 'POST',
    body: JSON.stringify({ refresh_token }),
  }).catch(() => undefined)
  window.localStorage.removeItem('solvable_session_token')
  window.localStorage.removeItem('solvable_refresh_token')
}
