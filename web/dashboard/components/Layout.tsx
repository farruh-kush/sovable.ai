import React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'

const groups = [
  { label: 'Workspace', items: [['/dashboard', 'Overview'], ['/dashboard/playground', 'Playground'], ['/dashboard/models', 'Models catalog'], ['/dashboard/usage', 'Usage & analytics']] },
  { label: 'Account', items: [['/dashboard/keys', 'API keys'], ['/dashboard/billing', 'Billing'], ['/dashboard/team', 'Team & roles'], ['/dashboard/privacy', 'Privacy & masking'], ['/dashboard/agents', 'Agents & apps'], ['/dashboard/security', 'Security & sessions']] },
  { label: 'Administration', items: [['/admin', 'Platform overview'], ['/admin/organizations', 'Organizations'], ['/admin/users', 'Users & RBAC'], ['/admin/providers', 'Providers'], ['/admin/models', 'Models & pricing'], ['/admin/routing', 'Routing policy'], ['/admin/privacy', 'Privacy governance']] },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
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
      <header className="topbar"><div><span className="eyebrow">SOVEREIGN AI INFRASTRUCTURE</span><h1>Unified intelligence layer</h1></div><div className="top-actions"><Link href="/" className="text-link">sovable.ai</Link><span className="avatar">FA</span></div></header>
      <div className="content">{children}</div>
    </main>
  </div>
}
