import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'

const groups = [
  { label: 'Workspace', items: [['/dashboard', 'Overview'], ['/dashboard/playground', 'Playground'], ['/dashboard/models', 'Models catalog'], ['/dashboard/usage', 'Usage & analytics']] },
  { label: 'Account', items: [['/dashboard/keys', 'API keys'], ['/dashboard/billing', 'Billing'], ['/dashboard/team', 'Team & roles'], ['/dashboard/privacy', 'Privacy & masking'], ['/dashboard/agents', 'Agents & apps'], ['/dashboard/security', 'Security & sessions']] },
  { label: 'Administration', items: [['/admin', 'Platform overview'], ['/admin/organizations', 'Organizations'], ['/admin/users', 'Users & RBAC'], ['/admin/providers', 'Providers'], ['/admin/models', 'Models & pricing'], ['/admin/routing', 'Routing policy'], ['/admin/privacy', 'Privacy governance']] },
]

const authBase = process.env.NEXT_PUBLIC_AUTH_BASE_URL || 'https://api.sovable.ai'

export default function Layout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [user, setUser] = useState<{ display_name?: string; email?: string } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = window.localStorage.getItem('solvable_session_token')
    if (!token) { setLoading(false); return }
    fetch(`${authBase}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(response => response.ok ? response.json() : Promise.reject(new Error('session expired')))
      .then(setUser)
      .catch(() => { window.localStorage.removeItem('solvable_session_token'); window.localStorage.removeItem('solvable_refresh_token') })
      .finally(() => setLoading(false))
  }, [])

  async function logout() {
    const refresh_token = window.localStorage.getItem('solvable_refresh_token')
    try { await fetch(`${authBase}/auth/logout`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token }) }) } finally {
      window.localStorage.removeItem('solvable_session_token')
      window.localStorage.removeItem('solvable_refresh_token')
      setUser(null)
      await router.push('/auth/login')
    }
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <Link href="/" className="brand"><span className="brand-mark">S</span><span>Solvable <em>AI</em></span></Link>
      <div className="side-caption">AI CONTROL PLANE</div>
      <nav className="side-nav">
        {groups.map(group => <div className="nav-group" key={group.label}>
          <span className="nav-label">{group.label}</span>
          {group.items.map(([href, label]) => <Link key={href} href={href} className={router.pathname === href ? 'active' : ''}>{label}</Link>)}
        </div>)}
      </nav>
      <div className="side-bottom"><div className="status-dot" /> All systems ready<div className="side-note">Gateway · Router · Providers</div></div>
    </aside>
    <main className="main-panel">
      <header className="topbar"><div><span className="eyebrow">SOVEREIGN AI INFRASTRUCTURE</span><h1>Unified intelligence layer</h1></div><div className="top-actions"><Link href="/" className="text-link">sovable.ai</Link>{loading ? <span className="auth-pill">Checking session…</span> : user ? <><span className="auth-user">{user.display_name || user.email || 'Account'}</span><button className="text-button" onClick={logout}>Log out</button></> : <><Link href="/auth/login" className="text-link">Sign in</Link><Link href="/auth/register" className="button primary compact">Create account</Link></>}</div></header>
      <div className="content">{children}</div>
    </main>
  </div>
}
