import React from 'react'

export default function UsageChart(){
  // Placeholder simple chart using CSS bars; replace with charting lib later
  const sample = [120, 80, 200, 160, 90, 30, 60]
  const max = Math.max(...sample)
  return (
    <section>
      <h2>Usage (last 7 days)</h2>
      <div style={{display:'flex', gap:8, alignItems:'end', height:120}}>
        {sample.map((v,i)=> (
          <div key={i} style={{flex:1, textAlign:'center'}}>
            <div style={{height: (v/max*100) + '%', background:'#0b84ff', borderRadius:4}} />
            <div style={{fontSize:12}}>{v}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
