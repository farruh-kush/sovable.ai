import React from 'react';
import Link from 'next/link';

export default function Home() {
  return (
    <main style={{fontFamily: 'system-ui, sans-serif', padding: 24}}>
      <h1>AI Routing Layer — Dashboard</h1>
      <p>This is a starter Next.js dashboard. Use it to build marketing pages and the developer dashboard.</p>
      <ul>
        <li><Link href="/dashboard">Open Dashboard</Link></li>
        <li><a href="/api/health">/v1/health (proxy through backend)</a></li>
      </ul>
    </main>
  );
}
