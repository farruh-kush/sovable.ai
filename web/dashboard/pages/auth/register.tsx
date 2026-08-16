import Link from 'next/link'
import { useState } from 'react'

export default function RegisterPage() {
  const [channel, setChannel] = useState<'email' | 'phone'>('email')
  const [destination, setDestination] = useState('')
  const [message, setMessage] = useState('')
  const authBase = process.env.NEXT_PUBLIC_AUTH_BASE_URL || '/auth'
  async function submit(event: React.FormEvent) { event.preventDefault(); if (!destination) return; setMessage('Verification is ready. Connect the auth service delivery provider to send the code.') }
  return <main className="auth-shell"><section className="auth-card"><Link href="/" className="brand"><span className="brand-mark">S</span><span>Solvable <em>AI</em></span></Link><span className="eyebrow">CREATE YOUR CONTROL PLANE</span><h1>Start with your identity</h1><p className="muted">Create an account with email, phone, Google, or Apple. Organization setup comes next.</p><div className="oauth-grid"><a className="button secondary" href={`${authBase}/oauth/google/start`}>Sign up with Google</a><a className="button secondary" href={`${authBase}/oauth/apple/start`}>Sign up with Apple</a></div><div className="auth-divider"><span>or verify directly</span></div><div className="segmented"><button className={channel === 'email' ? 'active' : ''} onClick={() => setChannel('email')}>Email</button><button className={channel === 'phone' ? 'active' : ''} onClick={() => setChannel('phone')}>Phone</button></div><form onSubmit={submit}><label>{channel === 'email' ? 'Email address' : 'Phone number'}<input value={destination} onChange={event => setDestination(event.target.value)} placeholder={channel === 'email' ? 'you@company.com' : '+14155550123'} required /></label><button className="button primary" type="submit">Send verification code</button></form>{message && <div className="data-state">{message}</div>}<p className="auth-foot">Already have an account? <Link href="/auth/login">Sign in</Link></p></section></main>
}
