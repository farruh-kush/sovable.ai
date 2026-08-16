import { useEffect, useState } from 'react'
import Layout from '../components/Layout'
import { getAdminOverview } from '../lib/api'

type Provider = {
  name: string
  configured: boolean
  circuit_open: boolean
  error_count: number
  last_latency_ms?: number | null
}
type Policy = { alias: string; strategy: string; primary?: string; fallback?: string[]; candidates?: string[] }
type Model = { id: string; provider?: string; data_policy?: { trains_on_data?: boolean } }
type Overview = {
  generated_at?: string
  providers?: Provider[]
  models?: { data?: Model[] }
  routing?: { policies?: Policy[]; pricing?: { providers?: string[] } }
  summary?: { providers_total: number; providers_configured: number; circuits_open: number; models_total: number }
  router?: { status?: string }
}

export default function Admin() {
  const [key, setKey] = useState('')
  const [data, setData] = useState<Overview | null>(null)
  const [tab, setTab] = useState('Operations')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (typeof window !== 'undefined') setKey(localStorage.getItem('solvable_admin_key') || '')
  }, [])

  async function connect() {
    setBusy(true)
    setError('')
    try {
      if (typeof window !== 'undefined') localStorage.setItem('solvable_admin_key', key)
      setData(await getAdminOverview())
    } catch (exception: any) {
      setData(null)
      setError(exception?.response?.status === 403 ? 'Admin key rejected. Check the management key and try again.' : 'Admin overview is unavailable. Confirm gateway and internal service health.')
    } finally {
      setBusy(false)
    }
  }

  const providers = data?.providers || []
  const models = data?.models?.data || []
  const policies = data?.routing?.policies || []
  const summary = data?.summary

  return (
    <Layout>
      <div className="section-heading">
        <div><span className="eyebrow">ADMIN / OPERATIONS</span><h2>Control plane posture</h2><p>Inspect provider readiness, routing policy, model coverage, and safe operational signals from one governed view.</p></div>
        <div className="admin-toolbar"><span className="pill">{data?.generated_at ? new Date(data.generated_at).toLocaleTimeString() : 'Not connected'}</span><button className="button secondary" onClick={connect} disabled={busy}>{busy ? 'Refreshing…' : 'Refresh snapshot'}</button></div>
      </div>
      <div className="admin-keybar card"><div><strong>Management access</strong><span className="muted">Stored only in this browser and sent as X-Admin-Key.</span></div><input type="password" value={key} onChange={event => setKey(event.target.value)} placeholder="Enter admin API key" /><button className="button primary" onClick={connect} disabled={busy}>Connect</button></div>
      {error && <div className="notice error">{error}</div>}
      <div className="admin-tabs">{['Operations', 'Providers', 'Routing policy', 'Model catalog', 'Audit trail'].map(item => <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}</button>)}</div>
      {!data && !error && <div className="empty card">Connect with an admin key to load the live control-plane snapshot.</div>}
      {data && tab === 'Operations' && <Operations data={data} providers={providers} policies={policies} summary={summary} />}
      {data && tab === 'Providers' && <section className="card table-card"><Header eyebrow="PROVIDER REGISTRY" title="Configured adapters" /><ProviderTable providers={providers} /></section>}
      {data && tab === 'Routing policy' && <section className="card table-card"><Header eyebrow="POLICY ENGINE" title="Static, cost, and latency routes" count={`${data.routing?.pricing?.providers?.length || 0} providers priced`} /><PolicyTable policies={policies} /></section>}
      {data && tab === 'Model catalog' && <section className="card table-card"><Header eyebrow="MODEL CATALOG" title="Available models and data policy" count={`${models.length} models`} /><ModelTable models={models} /></section>}
      {data && tab === 'Audit trail' && <section className="card empty-state"><span className="eyebrow">AUDIT TRAIL</span><h3>Append-only evidence is the next control-plane slice.</h3><p>This surface is reserved for request, policy, billing, and administrative audit events. Raw prompts and provider credentials remain excluded.</p><span className="pill">Schema defined · ingestion pending</span></section>}
    </Layout>
  )
}

function Operations({ data, providers, policies, summary }: { data: Overview; providers: Provider[]; policies: Policy[]; summary?: Overview['summary'] }) {
  return <><div className="metric-grid"><Metric label="Provider coverage" value={`${summary?.providers_configured || 0}/${summary?.providers_total || 0}`} note="Configured adapters" tone={summary?.providers_configured ? 'positive' : 'negative'} /><Metric label="Models registered" value={summary?.models_total || 0} note="Live routing catalog" /><Metric label="Open circuits" value={summary?.circuits_open || 0} note={summary?.circuits_open ? 'Failover attention required' : 'No circuit breakers open'} tone={summary?.circuits_open ? 'negative' : 'positive'} /><Metric label="Router status" value={data.router?.status || '—'} note="Internal health signal" tone="positive" /></div><div className="dashboard-grid"><section className="card"><Header eyebrow="PROVIDER HEALTH" title="Adapter readiness" count={`${providers.length} registered`} /><ProviderTable providers={providers} /></section><section className="card"><Header eyebrow="ROUTING" title="Policy coverage" count={`${policies.length} routes`} /><PolicyList policies={policies.slice(0, 6)} /></section></div></>
}
function Metric({ label, value, note, tone = '' }: { label: string; value: string | number; note: string; tone?: string }) { return <div className="metric-card"><span>{label}</span><strong>{value}</strong><small className={tone}>{note}</small></div> }
function Header({ eyebrow, title, count }: { eyebrow: string; title: string; count?: string }) { return <div className="table-title"><div><span className="eyebrow">{eyebrow}</span><h3>{title}</h3></div>{count && <span className="pill">{count}</span>}</div> }
function ProviderTable({ providers }: { providers: Provider[] }) { return providers.length ? <div className="table-wrap"><table><thead><tr><th>Provider</th><th>State</th><th>Errors</th><th>Latency</th></tr></thead><tbody>{providers.map(item => <tr key={item.name}><td><strong>{item.name}</strong><small>{item.configured ? 'Credential configured' : 'Credential not configured'}</small></td><td><span className={`status-label ${item.circuit_open ? 'negative' : item.configured ? 'positive' : 'warning'}`}>{item.circuit_open ? 'Circuit open' : item.configured ? 'Healthy' : 'Not configured'}</span></td><td>{item.error_count}</td><td>{item.last_latency_ms ? `${Math.round(item.last_latency_ms)} ms` : '—'}</td></tr>)}</tbody></table></div> : <div className="empty">Provider health unavailable.</div> }
function PolicyList({ policies }: { policies: Policy[] }) { return policies.length ? <div className="model-list">{policies.map(item => <div className="model-row" key={item.alias}><span className="model-dot" /><div><strong>{item.alias}</strong><small>{item.strategy} · {item.primary || (item.candidates || []).join(', ') || 'managed route'}</small></div><span className="arrow">→</span></div>)}</div> : <div className="empty">Routing policy unavailable.</div> }
function PolicyTable({ policies }: { policies: Policy[] }) { return policies.length ? <div className="table-wrap"><table><thead><tr><th>Alias</th><th>Strategy</th><th>Primary / candidates</th><th>Fallback</th></tr></thead><tbody>{policies.map(item => <tr key={item.alias}><td><strong>{item.alias}</strong></td><td><span className="pill">{item.strategy}</span></td><td>{item.primary || (item.candidates || []).join(', ') || '—'}</td><td>{item.fallback?.join(' → ') || 'None'}</td></tr>)}</tbody></table></div> : <div className="empty">No routing policies returned.</div> }
function ModelTable({ models }: { models: Model[] }) { return models.length ? <div className="table-wrap"><table><thead><tr><th>Model</th><th>Provider</th><th>Data policy</th></tr></thead><tbody>{models.map(item => <tr key={item.id}><td><strong>{item.id}</strong></td><td>{item.provider || '—'}</td><td>{item.data_policy?.trains_on_data ? 'Training permitted' : 'Policy tagged'}</td></tr>)}</tbody></table></div> : <div className="empty">Model catalog unavailable.</div> }
