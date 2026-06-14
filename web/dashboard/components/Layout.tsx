import React from 'react';
import Link from 'next/link';

export default function Layout({children}:{children:React.ReactNode}){
  return (
    <div style={{maxWidth:900, margin:'0 auto', padding:24}}>
      <header style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
        <h2><Link href="/">AI Routing Layer</Link></h2>
        <nav>
          <Link href="/dashboard">Dashboard</Link>
        </nav>
      </header>
      <hr />
      <div>{children}</div>
    </div>
  )
}
