import Link from 'next/link'
import { useState } from 'react'
import { useRouter } from 'next/router'
import { authBase, startVerification, verifyVerification } from '../lib/auth'

type Props = { mode: 'login' | 'register'; accountType: 'user' | 'admin'; title: string; eyebrow: string; successHref: string }

function MailIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m4 7 8 6 8-6" /></svg> }
function PhoneIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="3" width="10" height="18" rx="2" /><path d="M10 6h4M11 18h2" /></svg> }
function ShieldIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 20 6v5c0 5-3.3 8.2-8 10-4.7-1.8-8-5-8-10V6l8-3Z" /><path d="m9 12 2 2 4-4" /></svg> }
function GoogleIcon() { return <span className="auth-ref-google" aria-hidden="true">G</span> }
function AppleIcon() { return <span className="auth-ref-apple" aria-hidden="true">●</span> }

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
  const isRegister = mode === 'register'

  async function sendCode(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      const result = await startVerification(channel, destination, isRegister ? 'registration' : 'login', accountType)
      setStep('code')
      setMessage(result.dev_code ? `Development verification code: ${result.dev_code}` : `Verification code requested via ${result.delivery || 'the configured delivery provider'}.`)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not send a verification code.') }
    finally { setBusy(false) }
  }

  async function verify(event: React.FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      await verifyVerification(channel, destination, code, isRegister ? 'registration' : 'login', displayName || undefined, accountType)
      await router.push(successHref)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Verification failed.') }
    finally { setBusy(false) }
  }

  const alternateHref = isRegister ? (isAdmin ? '/admin/login' : '/portal/login') : (isAdmin ? '/admin/register' : '/portal/register')
  const alternateText = isRegister ? 'Already have an account?' : "Don't have an account?"
  const fieldLabel = channel === 'email' ? 'Email address' : 'Phone number'
  const fieldPlaceholder = channel === 'email' ? 'Enter your email' : 'Enter your phone number'
  return <main className="auth-ref-shell"><section className={`auth-ref-card ${isAdmin ? 'auth-ref-admin' : 'auth-ref-user'}`}><Link href="/" className="auth-ref-brand"><span className="auth-ref-mark">S</span><span>Solvable <em>AI</em></span></Link><span className="auth-ref-eyebrow">{eyebrow}</span><h1>{title}</h1><p className="auth-ref-subtitle">{isAdmin ? 'Organization administration for your team and AI workspace.' : 'One secure identity for your AI workspace.'}</p>{isRegister && <div className="auth-ref-account-type"><ShieldIcon /><div><strong>{isAdmin ? 'Admin Portal account' : 'User Portal account'}</strong><span>{isAdmin ? 'Creates an organization-admin identity.' : 'Creates a standard user identity.'}</span></div></div>}<div className="auth-ref-methods"><button type="button" className={channel === 'email' ? 'active' : ''} onClick={() => { setChannel('email'); setStep('destination'); setMessage('') }}><MailIcon />Email</button><button type="button" className={channel === 'phone' ? 'active' : ''} onClick={() => { setChannel('phone'); setStep('destination'); setMessage('') }}><PhoneIcon />Phone</button></div>{step === 'destination' ? <form className="auth-ref-form" onSubmit={sendCode}>{isRegister && <label className="auth-ref-field"><span className="auth-ref-icon"><ShieldIcon /></span><input value={displayName} onChange={event => setDisplayName(event.target.value)} placeholder="Enter your name" aria-label="Display name" required /></label>}<label className="auth-ref-field"><span className="auth-ref-icon">{channel === 'email' ? <MailIcon /> : <PhoneIcon />}</span><input type={channel === 'email' ? 'email' : 'tel'} value={destination} onChange={event => setDestination(event.target.value)} placeholder={fieldPlaceholder} aria-label={fieldLabel} required /></label>{!isRegister && <Link href="#recovery" className="auth-ref-forgot">Forgot how to sign in?</Link>}<button className="auth-ref-submit" type="submit" disabled={busy}>{busy ? 'Sending…' : isRegister ? 'Create account' : 'Sign in'}</button></form> : <form className="auth-ref-form" onSubmit={verify}><label className="auth-ref-field"><span className="auth-ref-icon"><ShieldIcon /></span><input inputMode="numeric" pattern="[0-9]{6}" maxLength={6} value={code} onChange={event => setCode(event.target.value)} placeholder="Enter verification code" aria-label="Verification code" required /></label><button className="auth-ref-submit" type="submit" disabled={busy}>{busy ? 'Verifying…' : isRegister ? 'Verify and create account' : 'Verify and sign in'}</button><button className="auth-ref-secondary" type="button" onClick={() => setStep('destination')}>Use a different {channel}</button></form>}{message && <div className="auth-ref-message">{message}</div>}<p className="auth-ref-account-link">{alternateText} <Link href={alternateHref}>{isRegister ? 'Sign in' : 'Sign up'}</Link></p>{!isAdmin && <><div className="auth-ref-or"><span>or</span></div><div className="auth-ref-socials"><a href={`${authBase}/auth/oauth/google/start`}><GoogleIcon />Continue with Google</a><a href={`${authBase}/auth/oauth/apple/start`}><AppleIcon />Continue with Apple</a></div></>}<p className="auth-ref-terms">By continuing, you agree to Solvable’s <Link href="#terms">Terms of Service</Link> and <Link href="#privacy">Privacy Policy</Link>.</p><p className="auth-ref-portal-link"><Link href={isAdmin ? '/controller' : '/admin'}>{isAdmin ? 'Platform Controller entry' : 'Admin Portal entry'}</Link></p></section></main>
}
