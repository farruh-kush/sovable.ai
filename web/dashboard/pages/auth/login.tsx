import Link from 'next/link'
import { useState } from 'react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const authBase = process.env.NEXT_PUBLIC_AUTH_BASE_URL || '/auth'
  return <main className="auth-shell"><section className="auth-card"><Link href="/" className="brand"><span className="brand-mark">S</span><span>Solvable <em>AI</em></span></Link><span className="eyebrow">WELCOME BACK</span><h1>Sign in to your control plane</h1><p className="muted">Use a verified email, phone number, or an identity provider.</p><div className="oauth-grid"><a className="button secondary" href={`${authBase}/oauth/google/start`}>Continue with Google</a><a className="button secondary" href={`${authBase}/oauth/apple/start`}>Continue with Apple</a></div><div className="auth-divider"><span>or continue with email</span></div><form onSubmit={event => { event.preventDefault(); setMessage(email ? 'A verification code will be sent when the identity service is configured.' : 'Enter your email address.') }}><label>Email address<input type="email" value={email} onChange={event => setEmail(event.target.value)} placeholder="you@company.com" required /></label><button className="button primary" type="submit">Send sign-in code</button></form>{message && <div className="data-state">{message}</div>}<p className="auth-foot">New to Solvable? <Link href="/auth/register">Create an account</Link></p></section></main>
}
