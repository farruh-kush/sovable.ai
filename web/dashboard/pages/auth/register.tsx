import Link from 'next/link'
import { useState } from 'react'
import { useRouter } from 'next/router'
import { startVerification, verifyVerification, authBase } from '../../lib/auth'

export default function RegisterPage() {
  const router = useRouter()
  const [channel, setChannel] = useState<'email' | 'phone'>('email')
  const [destination, setDestination] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState<'destination' | 'code'>('destination')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  async function sendCode(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try { const result = await startVerification(channel, destination, 'registration'); setStep('code'); setMessage(result.dev_code ? `Development verification code: ${result.dev_code}` : `Verification code requested via ${result.delivery || 'the configured delivery provider'}.`) }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Could not send a verification code.') }
    finally { setBusy(false) }
  }

  async function verify(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try { await verifyVerification(channel, destination, code, 'registration', displayName || undefined); await router.push('/dashboard') }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Verification failed.') }
    finally { setBusy(false) }
  }

  return <main className="auth-shell"><section className="auth-card"><Link href="/" className="brand"><span className="brand-mark">S</span><span>Solvable <em>AI</em></span></Link><span className="eyebrow">CREATE YOUR CONTROL PLANE</span><h1>Start with your identity</h1><p className="muted">Create an account with email, phone, Google, or Apple. Organization setup comes next.</p><div className="oauth-grid"><a className="button secondary" href={`${authBase}/auth/oauth/google/start`}>Sign up with Google</a><a className="button secondary" href={`${authBase}/auth/oauth/apple/start`}>Sign up with Apple</a></div><div className="auth-divider"><span>or verify directly</span></div><div className="segmented"><button className={channel === 'email' ? 'active' : ''} onClick={() => { setChannel('email'); setStep('destination') }}>Email</button><button className={channel === 'phone' ? 'active' : ''} onClick={() => { setChannel('phone'); setStep('destination') }}>Phone</button></div>{step === 'destination' ? <form onSubmit={sendCode}><label>Display name<input value={displayName} onChange={event => setDisplayName(event.target.value)} placeholder="Your name" /></label><label>{channel === 'email' ? 'Email address' : 'Phone number'}<input type={channel === 'email' ? 'email' : 'tel'} value={destination} onChange={event => setDestination(event.target.value)} placeholder={channel === 'email' ? 'you@company.com' : '+14155550123'} required /></label><button className="button primary" type="submit" disabled={busy}>{busy ? 'Sending…' : 'Send verification code'}</button></form> : <form onSubmit={verify}><label>Verification code<input inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={code} onChange={event => setCode(event.target.value)} placeholder="123456" required /></label><button className="button primary" type="submit" disabled={busy}>{busy ? 'Creating account…' : 'Verify and create account'}</button><button className="button secondary" type="button" onClick={() => setStep('destination')}>Use a different destination</button></form>}{message && <div className="data-state">{message}</div>}<p className="auth-foot">Already have an account? <Link href="/auth/login">Sign in</Link></p><p className="auth-foot"><Link href="/">Return to sovable.ai</Link></p></section></main>
}
