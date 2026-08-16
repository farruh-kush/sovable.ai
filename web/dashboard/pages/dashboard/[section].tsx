import { useEffect, useState } from 'react'
import Layout from '../../components/Layout'
import { api, getModels } from '../../lib/api'

const pages: Record<string, { eyebrow: string; title: string; description: string; cards: [string, string, string][] }> = {
  models: { eyebrow: 'MODEL CATALOG', title: 'Models built for governed use', description: 'Browse the available provider models and the policy envelope applied to each route.', cards: [['Catalog', 'Provider-backed model inventory', 'Live'], ['Data policy', 'Masking and retention eligibility', 'Governed'], ['Routing', 'Preferred aliases and fallbacks', 'Policy-driven']] },
  usage: { eyebrow: 'USAGE & ANALYTICS', title: 'Understand every request', description: 'Follow token usage, latency, cache behavior, and provider outcomes from one control surface.', cards: [['Requests', 'Request volume by time window', 'Event-backed'], ['Spend', 'Provider cost and markup visibility', 'Budget-aware'], ['Reliability', 'Latency and error trends', 'Observable']] },
  billing: { eyebrow: 'BILLING', title: 'Budgets with customer control', description: 'Manage plan, usage thresholds, invoices, and cost controls without losing provider-level detail.', cards: [['Current plan', 'Free quota and pay-as-you-go controls', 'Configured'], ['Budget guardrails', 'Monthly cap and alert thresholds', 'Protected'], ['Invoices', 'Usage exports and invoice history', 'Coming with billing events']] },
  team: { eyebrow: 'TEAM & ROLES', title: 'Collaborate with least privilege', description: 'Invite members, assign organization roles, and make access changes auditable.', cards: [['Members', 'Owners, admins, builders, viewers', 'RBAC'], ['Organizations', 'Tenant and workspace boundaries', 'Isolated'], ['Invitations', 'Time-limited, single-use invites', 'Secure']] },
  privacy: { eyebrow: 'PRIVACY & MASKING', title: 'Keep sensitive data under policy', description: 'Review masking behavior, classifications, provider eligibility, and restoration controls.', cards: [['Classification', 'PII, secrets, regulated and internal data', 'Policy'], ['Transformations', 'Redaction, tokenization, hashing and blocking', 'Enforced'], ['Provider boundary', 'Allowed destinations by policy', 'Governed']] },
  agents: { eyebrow: 'AGENTS & APPS', title: 'Extend the control plane safely', description: 'Install governed applications and agents with explicit permissions, tools, data boundaries, and side-effect levels.', cards: [['Store', 'Discover reviewed packages', 'Review-gated'], ['Permissions', 'Tools and data scopes', 'Least privilege'], ['Runs', 'Execution evidence and rollback', 'Auditable']] },
  security: { eyebrow: 'SECURITY & SESSIONS', title: 'Protect identity and access', description: 'Review active sessions, linked sign-in methods, API keys, and security events.', cards: [['Sessions', 'Active browsers and revocation', 'Protected'], ['Sign-in methods', 'Email, phone, Google and Apple', 'Extensible'], ['Recovery', 'Verified recovery and step-up controls', 'Secure']] },
}

export default function UserSection({ section }: { section: string }) {
  const config = pages[section] || pages.models
  const [models, setModels] = useState<any[]>([])
  const [state, setState] = useState<'loading' | 'ready' | 'empty' | 'error'>('loading')
  useEffect(() => {
    if (section !== 'models') { setState('ready'); return }
    getModels().then(data => { setModels(data?.data || data?.models || data || []); setState('ready') }).catch(() => setState('error'))
  }, [section])
  return <Layout>
    <section className="section-hero"><div><span className="eyebrow">{config.eyebrow}</span><h2>{config.title}</h2><p>{config.description}</p></div><span className="pill">Customer-controlled</span></section>
    <section className="feature-grid">{config.cards.map(([label, detail, status]) => <article className="feature-card" key={label}><div className="feature-icon">{label.slice(0, 1)}</div><div><span className="eyebrow">{label}</span><h3>{detail}</h3><span className="status-label positive">{status}</span></div></article>)}</section>
    {section === 'models' ? <section className="card table-card"><div className="table-title"><div><span className="eyebrow">LIVE CATALOG</span><h3>Available models</h3></div><span className="pill">{state === 'ready' ? `${models.length} returned` : state}</span></div>{state === 'error' ? <div className="data-state error">Model service unavailable. Retry when the gateway is healthy.</div> : state === 'loading' ? <div className="data-state">Loading governed catalog…</div> : models.length ? <div className="table-wrap"><table><thead><tr><th>Model</th><th>Provider</th><th>Context</th><th>Policy</th></tr></thead><tbody>{models.map((item: any) => <tr key={item.id || item.model}><td><strong>{item.id || item.model}</strong></td><td>{item.provider || 'Managed route'}</td><td>{item.context_length || '—'}</td><td><span className="status-label positive">Eligible</span></td></tr>)}</tbody></table></div> : <div className="data-state">No models are currently returned by the provider catalog.</div>}</section> : <section className="dashboard-grid"><article className="card"><span className="eyebrow">NEXT ACTION</span><h3>Connect this surface to governed events</h3><p className="muted">This screen is ready for the control-plane API contract. It intentionally avoids fabricated metrics until the corresponding event stream is available.</p><button className="button secondary" onClick={() => alert('This control is ready for the next API slice.')}>Review contract</button></article><article className="card"><span className="eyebrow">CONTROL STATUS</span><h3>Policy boundary active</h3><p className="muted">All provider calls remain behind the gateway, router, privacy policy, and billing controls.</p><span className="status-label positive">Protected path</span></article></section>}
  </Layout>
}

export function getStaticPaths() { return { paths: Object.keys(pages).map(section => ({ params: { section } })), fallback: false } }
export function getStaticProps({ params }: { params: { section: string } }) { return { props: { section: params.section } } }
