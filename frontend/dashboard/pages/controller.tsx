import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getAdminOverview } from '../lib/api'

export default function PlatformController() {
  const [key, setKey] = useState('')
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState('')
  const [summary, setSummary] = useState<{ providers_total?: number; providers_configured?: number; models_total?: number; circuits_open?: number } | null>(null)
  useEffect(() => { setKey(window.localStorage.getItem('solvable_controller_key') || '') }, [])
  async function connect() {
    setError(''); window.localStorage.setItem('solvable_controller_key', key); window.localStorage.setItem('solvable_admin_key', key)
    try { const result = await getAdminOverview(); setSummary(result.summary || null); setConnected(true) }
    catch (exception: any) { setConnected(false); setError(exception?.response?.status === 403 ? 'Controller credential rejected.' : 'Controller is unavailable.') }
  }
  function disconnect() { window.localStorage.removeItem('solvable_controller_key'); window.localStorage.removeItem('solvable_admin_key'); setKey(''); setConnected(false); setSummary(null) }
  return <main className="controller-shell"><header className="controller-header"><Link href="/" className="brand"><span className="brand-mark">S</span><span>Solvable <em>AI</em></span></Link><span className="controller-badge">PLATFORM CONTROLLER</span></header><section className="controller-card"><span className="eyebrow">SEPARATE OPERATIONS ENTRY</span><h1>Platform Controller</h1><p className="muted">This surface is isolated from the User Portal and Admin Portal. Use the platform management credential to inspect provider health, routing, model catalog, and reliability signals.</p><div className="data-state">Organization admins register at <Link href="/admin/register">/admin/register</Link>. Platform controller access is not self-registered.</div><label>Controller management key<input type="password" value={key} onChange={event => setKey(event.target.value)} placeholder="Enter platform controller key" /></label><div className="closing-actions"><button className="button primary" onClick={connect}>Enter controller</button>{connected && <button className="button secondary" onClick={disconnect}>Exit controller</button>}</div>{error && <div className="data-state error">{error}</div>}{connected && <div className="controller-grid"><div><span>Providers</span><strong>{summary?.providers_configured || 0}/{summary?.providers_total || 0}</strong></div><div><span>Models</span><strong>{summary?.models_total || 0}</strong></div><div><span>Open circuits</span><strong>{summary?.circuits_open || 0}</strong></div></div>}<p className="auth-foot"><Link href="/portal">Return to User Portal</Link> · <Link href="/admin">Open Admin Portal</Link></p></section></main>
}
