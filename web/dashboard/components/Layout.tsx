import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'

const groups = [
  { label: 'User Portal', tone: 'user', items: [['/portal', 'Portal home'], ['/dashboard', 'Workspace overview'], ['/dashboard/playground', 'Playground'], ['/dashboard/models', 'Model catalog'], ['/dashboard/usage', 'Usage & analytics']] },
  { label: 'Organization Admin', tone: 'admin', items: [['/admin', 'Admin overview'], ['/admin/providers', 'Providers & models'], ['/admin/routing', 'Routing policy'], ['/admin/billing', 'Budgets & billing'], ['/admin/agents', 'Installed agents'], ['/admin/audit', 'Audit trail']] },
  { label: 'Agent Creator', tone: 'creator', items: [['/creator', 'Marketplace & studio'], ['/creator/register', 'Create an agent']] },
  { label: 'Platform Controller', tone: 'controller', items: [['/controller', 'Operations console']] },
  { label: 'Account', tone: 'account', items: [['/dashboard/keys', 'API keys'], ['/dashboard/billing', 'Billing · UZS'], ['/dashboard/team', 'Team & roles'], ['/dashboard/privacy', 'Privacy & masking'], ['/dashboard/security', 'Security & sessions']] },
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
      .catch(() => {
        window.localStorage.removeItem('solvable_session_token')
        window.localStorage.removeItem('solvable_refresh_token')
      })
      .finally(() => setLoading(false))
  }, [])
  async function logout() {
    const refresh_token = window.localStorage.getItem('solvable_refresh_token')
    try {
      await fetch(`${authBase}/auth/logout`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token }) })
    } finally {
      window.localStorage.removeItem('solvable_session_token')
      window.localStorage.removeItem('solvable_refresh_token')
      setUser(null)
      await router.push('/portal/login')
    }
  }
  const active = (href: string) => router.pathname === href || router.pathname.startsWith(`${href}/`)
  return <div className="app-shell">
    <aside className="sidebar">
      <Link href="/" className="brand"><span className="brand-mark">S</span><span>Solvable <em>AI</em></span></Link>
      <Link href="/portals" className="portal-switcher"><span className="side-caption">PRODUCT SURFACES</span><strong>Switch portal</strong><span>Four governed entry points →</span></Link>
      <nav className="side-nav">
        {groups.map(group => <div className={`nav-group nav-group-${group.tone}`} key={group.label}>
          <span className="nav-label">{group.label}</span>
          {group.items.map(([href, label]) => <Link key={href} href={href} className={active(href) ? 'active' : ''}>{label}</Link>)}
        </div>)}
      </nav>
      <div className="side-bottom"><div className="status-dot" /> All systems ready<div className="side-note">Gateway · Router · Providers</div></div>
    </aside>
    <main className="main-panel">
      <header className="topbar"><div><span className="eyebrow">SOVEREIGN AI INFRASTRUCTURE</span><h1>Unified intelligence layer</h1></div><div className="top-actions"><Link href="/portals" className="text-link">All portals</Link><Link href="/" className="text-link">sovable.ai</Link>{loading ? <span className="auth-pill">Checking session…</span> : user ? <><span className="auth-user">{user.display_name || user.email || 'Account'}</span><button className="text-button" onClick={logout}>Log out</button></> : <><Link href="/portal/login" className="text-link">Sign in</Link><Link href="/portal/register" className="button primary compact">Create account</Link></>}</div></header>
      <div className="content">{children}</div>
    </main>
  </div>
}
