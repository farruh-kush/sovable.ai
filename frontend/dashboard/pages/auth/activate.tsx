import Link from 'next/link'
import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import { completeEmailActivation } from '../../lib/auth'

export default function ActivateAccountPage() {
  const router = useRouter()
  const [message, setMessage] = useState('Activating your Solvable AI account…')
  useEffect(() => {
    if (!router.isReady) return
    const token = typeof router.query.token === 'string' ? router.query.token : ''
    if (!token) { setMessage('This activation link is missing its token.'); return }
    completeEmailActivation(token).then(result => {
      setMessage('Your account is active. Redirecting…')
      const next = result.user?.role === 'org_admin' ? '/admin' : result.user?.role === 'agent_creator' ? '/creator' : '/portal'
      void router.replace(next)
    }).catch(error => setMessage(error instanceof Error ? error.message : 'This activation link could not be used.'))
  }, [router.isReady, router.query.token, router])
  return <main className="auth-ref-shell"><section className="auth-ref-card auth-ref-user"><Link href="/" className="auth-ref-brand"><span className="auth-ref-mark">S</span><span>Solvable <em>AI</em></span></Link><span className="auth-ref-eyebrow">ACCOUNT ACTIVATION</span><h1>Confirm your email</h1><p className="auth-ref-subtitle">{message}</p>{message.includes('could not') || message.includes('missing') ? <Link className="auth-ref-submit" href="/portal/register">Return to registration</Link> : null}</section></main>
}
