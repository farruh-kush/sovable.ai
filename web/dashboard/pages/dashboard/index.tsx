import React, {useEffect, useState} from 'react';
import Link from 'next/link'
import ApiKeyList from '../../components/ApiKeyList'
import UsageChart from '../../components/UsageChart'
import {getHealth} from '../../lib/api'

export default function Dashboard() {
  const [health, setHealth] = useState<any>('Loading...')

  useEffect(()=>{
    getHealth().then(h=>setHealth(h)).catch(e=>setHealth({error: String(e)}))
  },[])

  return (
    <main style={{padding:24}}>
      <h1>Dashboard</h1>
      <p>Developer dashboard: keys, usage, and playground.</p>
      <div style={{display:'flex', gap:24}}>
        <div style={{flex:1}}>
          <ApiKeyList />
          <div style={{marginTop:16}}>
            <Link href="/dashboard/keys">Manage keys</Link> • <Link href="/dashboard/playground">Playground</Link>
          </div>
        </div>
        <div style={{width:360}}>
          <UsageChart />
          <section style={{marginTop:16}}>
            <h3>Health</h3>
            <pre style={{fontSize:12}}>{JSON.stringify(health, null, 2)}</pre>
          </section>
        </div>
      </div>
    </main>
  );
}
