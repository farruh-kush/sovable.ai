import React, {useState} from 'react'
import {chatCompletion} from '../../lib/api'

export default function Playground(){
  const [prompt, setPrompt] = useState('Hello from dashboard')
  const [resp, setResp] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  async function run(){
    setLoading(true)
    setResp(null)
    try{
      const payload = {model: 'gpt-4o-mini', messages:[{role:'user', content: prompt}]}
      const r = await chatCompletion(payload)
      setResp(r)
    }catch(e){
      setResp({error: String(e)})
    }finally{setLoading(false)}
  }

  return (
    <section>
      <h1>Playground</h1>
      <p>Simple chat playground that posts to <code>/v1/chat/completions</code> with the developer key.</p>
      <textarea style={{width:'100%',height:120}} value={prompt} onChange={e=>setPrompt(e.target.value)} />
      <div style={{marginTop:8}}>
        <button onClick={run} disabled={loading}>Run</button>
      </div>
      <div style={{marginTop:12}}>
        {loading && <div>Running…</div>}
        {resp && <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(resp, null, 2)}</pre>}
      </div>
    </section>
  )
}
