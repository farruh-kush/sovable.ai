import React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'
export default function Layout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const items = [['/dashboard', 'Overview'], ['/dashboard/keys', 'API keys'], ['/dashboard/playground', 'Playground']]
  return <div className="app-shell"><aside className="sidebar"><Link href="/" className="brand"><span className="brand-mark">S</span><span>Solvable <em>AI</em></span></Link><div className="side-caption">AI CONTROL PLANE</div><nav className="side-nav">{items.map(([href, label]) => <Link key={href} href={href} className={router.pathname === href ? 'active' : ''}>{label}</Link>)}</nav><div className="side-bottom"><div className="status-dot" /> All systems ready<div className="side-note">Gateway · Router · Providers</div></div></aside><main className="main-panel"><header className="topbar"><div><span className="eyebrow">SOVEREIGN AI INFRASTRUCTURE</span><h1>Unified intelligence layer</h1></div><div className="top-actions"><Link href="/" className="text-link">solvable.ai</Link><span className="avatar">FA</span></div></header><div className="content">{children}</div></main></div>
}
