import Link from 'next/link'
import { useState } from 'react'
import { useRouter } from 'next/router'
import { authBase, startVerification, verifyVerification } from '../lib/auth'

type Props = { mode: 'login' | 'register'; accountType: 'user' | 'admin'; title: string; eyebrow: string; successHref: string }

export default function PortalAuthCard({ mode, accountType, title, eyebrow, successHref }: Props) {
  const router = useRouter()
  const [channel, setChannel] = useState<'email' | 'phone'>('email')
  const [destination, setDestination] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [code, setCode] = useState('')
  const [step, setStep] = useState<'destination' | 'code'>('destination')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const isAdmin = accountType === 'admin'

  async function sendCode(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      const result = await startVerification(channel, destination, mode === 'register' ? 'registration' : 'login', accountType)
      setStep('code')
      setMessage(result.dev_code ? `Development verification code: ${result.dev_code}` : `Verification code requested via ${result.delivery || 'the configured delivery provider'}.`)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not send a verification code.') }
    finally { setBusy(false) }
  }

  async function verify(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      await verifyVerification(channel, destination, code, mode === 'register' ? 'registration' : 'login', displayName || undefined, accountType)
      await router.push(successHref)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Verification failed.') }
    finally { setBusy(false) }
  }

  const alternateHref = mode === 'register' ? (isAdmin ? '/admin/login' : '/portal/login') : (isAdmin ? '/admin/register' : '/portal/register')
  const alternateText = mode === 'register' ? 'Already registered? Sign in' : 'Need an account? Register here'
  return <main className="auth-shell"><section className={`auth-card portal-auth-card ${isAdmin ? 'admin-auth-card' : 'user-auth-card'}`}><Link href="/" className="brand"><span className="brand-mark">S</span><span>Solvable <em>AI</em></span></Link><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p className="muted">{isAdmin ? 'For organization owners and administrators. Platform operations use a separate controller entry.' : 'For developers and teams using the Solvable AI control plane.'}</p>{mode === 'register' && <div className="portal-purpose"><strong>{isAdmin ? 'Admin Portal account' : 'User Portal account'}</strong><span>{isAdmin ? 'Creates an organization-admin identity.' : 'Creates a standard user identity.'}</span></div>}{!isAdmin && <><div className="oauth-grid"><a className="button secondary" href={`${authBase}/auth/oauth/google/start`}>{mode === 'register' ? 'Sign up with Google' : 'Continue with Google'}</a><a className="button secondary" href={`${authBase}/auth/oauth/apple/start`}>{mode === 'register' ? 'Sign up with Apple' : 'Continue with Apple'}</a></div><div className="auth-divider"><span>or verify directly</span></div></>}{isAdmin && <div className="data-state">Admin SSO can be enabled after your organization’s verified domain and identity policy are configured.</div>}<div className="segmented"><button className={channel === 'email' ? 'active' : ''} onClick={() => { setChannel('email'); setStep('destination') }}>Email</button><button className={channel === 'phone' ? 'active' : ''} onClick={() => { setChannel('phone'); setStep('destination') }}>Phone</button></div>{step === 'destination' ? <form onSubmit={sendCode}>{mode === 'register' && <label>Display name<input value={displayName} onChange={event => setDisplayName(event.target.value)} placeholder="Your name" /></label>}<label>{channel === 'email' ? 'Email address' : 'Phone number'}<input type={channel === 'email' ? 'email' : 'tel'} value={destination} onChange={event => setDestination(event.target.value)} placeholder={channel === 'email' ? 'you@company.com' : '+14155550123'} required /></label><button className="button primary" type="submit" disabled={busy}>{busy ? 'Sending…' : 'Send verification code'}</button></form> : <form onSubmit={verify}><label>Verification code<input inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={code} onChange={event => setCode(event.target.value)} placeholder="123456" required /></label><button className="button primary" type="submit" disabled={busy}>{busy ? 'Verifying…' : mode === 'register' ? 'Verify and create account' : 'Verify and sign in'}</button><button className="button secondary" type="button" onClick={() => setStep('destination')}>Use a different destination</button></form>}{message && <div className="data-state">{message}</div>}<p className="auth-foot"><Link href={alternateHref}>{alternateText}</Link></p><p className="auth-foot"><Link href={isAdmin ? '/controller' : '/'}>{isAdmin ? 'Enter Platform Controller separately' : 'Return to sovable.ai'}</Link></p></section></main>
}
