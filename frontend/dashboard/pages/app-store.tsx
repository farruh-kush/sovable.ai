import Link from 'next/link'
import { useMemo, useState } from 'react'
import NationalShell, { Eyebrow, Pager } from '../components/NationalShell'
import { useLocale } from '../lib/locale'
import { trackEvent } from '../lib/analytics'

type Agent = {
  id: number
  name: string
  category: string
  outcome: string
  description: string
  languages: string
  data: string
  latency: string
  cost: string
  reviewed: string
  icon: string
}

const agents: Agent[] = [
  { id: 1, name: 'Citizen Helpdesk', category: 'Public services', outcome: 'Answer citizen questions', description: 'A governed assistant for public-service information with approved knowledge sources.', languages: 'UZ · RU · EN', data: 'Public', latency: 'Fast', cost: 'Low', reviewed: '18 Aug 2026', icon: '✦' },
  { id: 2, name: 'Clinical Navigator', category: 'Healthcare', outcome: 'Guide clinical operations', description: 'Summarizes approved clinical procedures and directs staff to the right workflow.', languages: 'UZ · RU', data: 'Restricted', latency: 'Balanced', cost: 'Medium', reviewed: '16 Aug 2026', icon: '◌' },
  { id: 3, name: 'Tender Analyst', category: 'Finance', outcome: 'Review tender documents', description: 'Extracts requirements, deadlines, risks, and decision evidence from tender packs.', languages: 'UZ · RU · EN', data: 'Confidential', latency: 'Balanced', cost: 'Medium', reviewed: '15 Aug 2026', icon: '▦' },
  { id: 4, name: 'Policy Translator', category: 'Government', outcome: 'Translate policy language', description: 'Creates controlled Uzbek, Russian, and English policy drafts with review checkpoints.', languages: 'UZ · RU · EN', data: 'Internal', latency: 'Fast', cost: 'Low', reviewed: '14 Aug 2026', icon: '中' },
  { id: 5, name: 'Company Copilot', category: 'Companies', outcome: 'Search internal knowledge', description: 'A private workspace copilot for company policies, procedures, and operational knowledge.', languages: 'UZ · RU · EN', data: 'Private', latency: 'Fast', cost: 'Medium', reviewed: '13 Aug 2026', icon: '⌁' },
  { id: 6, name: 'Supply Monitor', category: 'Industries', outcome: 'Detect supply risks', description: 'Highlights supply-chain exceptions and prepares an auditable action brief.', languages: 'UZ · RU', data: 'Internal', latency: 'Balanced', cost: 'Medium', reviewed: '12 Aug 2026', icon: '◈' },
]

export default function AppStore() {
  const { t } = useLocale()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')
  const [selected, setSelected] = useState<Agent | null>(null)
  const categories = ['All', ...Array.from(new Set(agents.map(agent => agent.category)))]
  const filtered = useMemo(() => agents.filter(agent => {
    const haystack = `${agent.name} ${agent.category} ${agent.outcome}`.toLowerCase()
    return (category === 'All' || agent.category === category) && haystack.includes(query.toLowerCase())
  }), [category, query])

  return <NationalShell><main className="national-page">
    <Eyebrow>{t('store.eyebrow')}</Eyebrow><h1>{t('store.title')}</h1><p className="national-lede">{t('store.lede')}</p>
    <div className="national-stats store-stats"><div><b>06</b><span>Verified agents</span></div><div><b>24/7</b><span>Governance review</span></div><div><b>UZ · RU · EN</b><span>Supported languages</span></div><div><b>3</b><span>Data sensitivity bands</span></div></div>
    <section className="app-store-frame"><aside className="app-store-rail"><div className="app-store-brand"><span className="national-logo">S</span><div><strong>{t('nav.appstore')}</strong><small>Governed agent catalog</small></div></div><Link href="/creator/login?next=%2Fcreator" className="national-button gold">＋ {t('common.creatorSignIn')}</Link><span className="rail-label">DISCOVER</span><span className="rail-item active">▦ Marketplace</span><span className="rail-item">✦ Featured</span><span className="rail-item">✓ Verified only</span><span className="rail-label">WHAT TO CHECK</span><span className="rail-note">Outcome · data class · latency · cost · last review</span></aside>
      <div className="app-store-main"><div className="app-store-toolbar"><label className="app-search">⌕<input aria-label="Search agents" value={query} onChange={event => { setQuery(event.target.value); trackEvent('app_store_search', { query: event.target.value }) }} placeholder="Search agents, outcomes, or sectors" /></label><select aria-label="Filter by category" className="store-filter" value={category} onChange={event => { setCategory(event.target.value); trackEvent('app_store_filter', { category: event.target.value }) }}>{categories.map(item => <option key={item}>{item}</option>)}</select></div><div className="store-hero"><Eyebrow>{t('store.heroEyebrow')}</Eyebrow><h2>Choose the outcome before the model.</h2><p>Every listing explains what it does, who can use it, how sensitive the data is, and what to expect before installation.</p></div><div className="store-heading"><h2>{filtered.length} agents available</h2><span>Sorted by verified review</span></div><div className="app-grid">{filtered.map(agent => <article className="app-card" key={agent.id}><div className="app-card-top"><span className="app-icon g-gold">{agent.icon}</span><div><h3>{agent.name}</h3><small>{agent.category}</small></div><span className="verified">VERIFIED</span></div><p>{agent.outcome}</p><div className="app-card-meta"><span>{agent.data}</span><span>{agent.latency}</span><span>{agent.cost} cost</span></div><small className="app-card-review">Reviewed {agent.reviewed} · {agent.languages}</small><div className="app-card-foot"><button type="button" onClick={() => { setSelected(agent); trackEvent('agent_detail_open', { agent: agent.name }) }}>View details</button><Link href="/portal/login?next=%2Fportal" onClick={() => trackEvent('agent_use_start', { agent: agent.name })}>Use agent →</Link></div></article>)}</div>{filtered.length === 0 && <div className="store-empty"><strong>No agents match this search.</strong><span>Try another outcome, sector, or data class.</span><button type="button" onClick={() => { setQuery(''); setCategory('All') }}>Clear filters</button></div>}{selected && <div className="agent-detail" role="dialog" aria-modal="true" aria-labelledby="agent-detail-title"><div><Eyebrow>AGENT DETAIL · VERIFIED</Eyebrow><h2 id="agent-detail-title">{selected.name}</h2><p>{selected.description}</p></div><button type="button" className="agent-detail-close" onClick={() => setSelected(null)} aria-label="Close agent detail">×</button><div className="agent-detail-grid"><div><small>Primary outcome</small><b>{selected.outcome}</b></div><div><small>Data sensitivity</small><b>{selected.data}</b></div><div><small>Expected latency</small><b>{selected.latency}</b></div><div><small>Cost band</small><b>{selected.cost}</b></div></div><Link className="national-button gold" href="/portal/login?next=%2Fportal" onClick={() => trackEvent('agent_install_start', { agent: selected.name })}>Sign in to use this agent →</Link></div>}</div></section><Pager previous={`01 · ${t('nav.overview')}`} previousHref="/" next={`03 · ${t('nav.aggregator')}`} nextHref="/aggregator" /></main></NationalShell>
}
