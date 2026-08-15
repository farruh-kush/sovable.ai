import { useState } from 'react'
import Layout from '../../components/Layout'
import { chatCompletion } from '../../lib/api'

export default function Playground() {
  const [prompt, setPrompt] = useState('Explain how intelligent model routing reduces cost without sacrificing reliability.')
  const [model, setModel] = useState('gpt-4o-mini')
  const [response, setResponse] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  async function run() { setLoading(true); setResponse(null); try { setResponse(await chatCompletion({ model, messages: [{ role: 'user', content: prompt }], temperature: 0.2 })) } catch (e: any) { setResponse({ error: e?.response?.data || e.message || 'Request failed' }) } finally { setLoading(false) } }
  return <Layout><div className="section-heading"><div><span className="eyebrow">DEVELOPER EXPERIENCE</span><h2>Routing playground</h2><p>Send an OpenAI-compatible request through the live gateway and inspect the normalized response.</p></div></div><div className="playground-grid"><div className="card form-card"><label>Model or route alias</label><input value={model} onChange={e => setModel(e.target.value)} /><label>Prompt</label><textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={9} /><div className="form-footer"><span className="muted">Uses the API key saved in this browser.</span><button className="button primary" onClick={run} disabled={loading}>{loading ? 'Routing…' : 'Run request →'}</button></div></div><div className="card response-card"><div className="table-title"><h3>Normalized response</h3>{response && <span className="pill">JSON</span>}</div><pre>{response ? JSON.stringify(response, null, 2) : 'Your response will appear here.'}</pre></div></div></Layout>
}
