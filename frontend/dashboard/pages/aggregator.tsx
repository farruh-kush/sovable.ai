import NationalShell, { Eyebrow, Pager } from '../components/NationalShell'
import { useLocale } from '../lib/locale'
import { Fragment, useState } from 'react'
import { trackEvent } from '../lib/analytics'

const providers = [
  { name: 'Navo’i LLM', role: 'Sovereign program', state: 'Healthy', latency: '420 ms', cost: 'Local cost band', tone: 'green' },
  { name: 'Qwen', role: 'China route', state: 'Healthy', latency: '610 ms', cost: 'Low cost band', tone: 'gold' },
  { name: 'Global fallback', role: 'Western route', state: 'Standby', latency: '840 ms', cost: 'Premium band', tone: 'navy' },
]

export default function Aggregator() {
  const { t } = useLocale()
  const [prompt, setPrompt] = useState('Please summarize the quarterly procurement report for our team.')
  const [ran, setRan] = useState(false)
  const masked = prompt.replace(/quarterly procurement report/gi, '[DOCUMENT]')
  return <NationalShell><main className="national-page"><Eyebrow>{t('agg.eyebrow')}</Eyebrow><h1>{t('agg.title')}</h1><p className="national-lede">{t('agg.lede')}</p>
    <section className="aggregator-task-hero"><div><Eyebrow>REQUEST INSPECTOR</Eyebrow><h2>See why the router chose a provider.</h2><p>Run a safe sample request and inspect masking, policy, route reason, latency, and fallback behavior before connecting your application.</p></div><div className="aggregator-status"><span className="status-pulse" /> Gateway operational <b>99.98%</b></div></section>
    <section className="route-inspector"><div className="route-input"><label htmlFor="route-prompt">Sample request</label><textarea id="route-prompt" value={prompt} onChange={event => setPrompt(event.target.value)} /><button type="button" className="national-button gold" onClick={() => { setRan(true); trackEvent('aggregator_sample_run', { promptLength: prompt.length }) }}>Run protected request →</button></div><div className="route-output"><div className="route-output-head"><span>INSPECTION TRACE</span><strong>{ran ? 'Completed' : 'Ready'}</strong></div><div className="trace-row"><small>01 · Input</small><p>{prompt}</p></div><div className="trace-row masked"><small>02 · PII masking</small><p>{ran ? masked : 'Names, emails, IDs, and sensitive document labels are masked before routing.'}</p></div><div className="trace-row"><small>03 · Route reason</small><p>{ran ? 'Navo’i LLM selected: local policy fit + healthy capacity + lowest protected-data exposure.' : 'Run the sample to reveal the route decision.'}</p></div><div className="trace-metrics"><span><b>{ran ? '420 ms' : '—'}</b><small>Latency</small></span><span><b>{ran ? 'Local' : '—'}</b><small>Cost band</small></span><span><b>{ran ? '0' : '—'}</b><small>Fallbacks</small></span></div></div></section>
    <section className="provider-health"><div className="section-heading"><div><Eyebrow>PROVIDER HEALTH</Eyebrow><h2>Routing capacity at a glance.</h2></div><span>Updated just now</span></div><div className="provider-health-grid">{providers.map(provider => <article className="provider-health-card" key={provider.name}><div><span className={`provider-dot ${provider.tone}`} /><h3>{provider.name}</h3></div><small>{provider.role}</small><div className="provider-health-meta"><span><b>{provider.state}</b> status</span><span><b>{provider.latency}</b> median</span><span><b>{provider.cost}</b></span></div></article>)}</div></section>
    <section className="workflow-card"><Eyebrow>{t('agg.pipeline')}</Eyebrow><div className="workflow-steps">{['Request','Mask','Route','Restore','Response'].map((step, index) => <Fragment key={step}><div className="workflow-step"><span>{`0${index + 1}`}</span><b>{step}</b><small>{['Protected input','Sensitive data removed','Policy decision','Safe output restore','Normalized response'][index]}</small></div>{index < 4 && <div className="workflow-arrow" aria-hidden="true">→</div>}</Fragment>)}</div></section>
    <Pager previous={`02 · ${t('nav.appstore')}`} previousHref="/app-store" next={`04 · ${t('nav.navoi')}`} nextHref="/navoi" /></main></NationalShell>
}
