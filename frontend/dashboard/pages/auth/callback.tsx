import { useEffect } from 'react'
import { useRouter } from 'next/router'

export default function AuthCallbackPage() {
  const router = useRouter()
  useEffect(() => {
    if (typeof window === 'undefined') return
    const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    const access = fragment.get('access_token')
    const refresh = fragment.get('refresh_token')
    if (access) localStorage.setItem('solvable_session_token', access)
    if (refresh) localStorage.setItem('solvable_refresh_token', refresh)
    router.replace('/dashboard')
  }, [router])
  return <main className="auth-shell"><section className="auth-card"><span className="eyebrow">AUTHENTICATING</span><h1>Securing your session…</h1><p className="muted">The control plane is completing your sign-in and will redirect you to the workspace.</p></section></main>
}
