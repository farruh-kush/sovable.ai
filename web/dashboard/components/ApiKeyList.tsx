import React, {useEffect, useState} from 'react'
import {listKeys, createKey} from '../lib/api'

export default function ApiKeyList(){
  const [keys, setKeys] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string|undefined>()
  const [newName, setNewName] = useState('')

  useEffect(()=>{
    setLoading(true)
    listKeys().then(data=>{
      if((data as any).error){
        setError((data as any).message || 'Error')
        setKeys([])
      }else{
        setKeys(data || [])
      }
    }).catch(e=>setError(String(e))).finally(()=>setLoading(false))
  },[])

  async function handleCreate(){
    setLoading(true)
    try{
      const res = await createKey(newName || 'web-ui')
      // backend may return raw key or object; push to list
      setKeys(prev=>[res, ...prev])
      setNewName('')
    }catch(e){
      setError(String(e))
    }finally{setLoading(false)}
  }

  return (
    <section>
      <h2>API Keys</h2>
      <p>Manage your API keys. Note: backend must implement /v1/keys for real data; this UI is resilient to missing endpoints.</p>
      <div style={{marginBottom:12}}>
        <input placeholder="Name (optional)" value={newName} onChange={e=>setNewName(e.target.value)} />
        <button onClick={handleCreate} disabled={loading} style={{marginLeft:8}}>Create key</button>
      </div>
      {loading && <div>Loading…</div>}
      {error && <div style={{color:'red'}}>{error}</div>}
      <ul>
        {keys.length===0 && !loading && <li>No keys found (or backend not available).</li>}
        {keys.map((k,i)=> (
          <li key={i} style={{marginBottom:8}}>
            <strong>{k.name || k.id || 'key'}</strong>
            <div style={{fontFamily:'monospace', fontSize:12}}>{k.key ?? JSON.stringify(k)}</div>
          </li>
        ))}
      </ul>
    </section>
  )
}
