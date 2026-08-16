import Link from 'next/link'
import { useRouter } from 'next/router'

const nav = [
  ['/', '01', 'Обзор'],
  ['/app-store', '02', 'AI App Store'],
  ['/aggregator', '03', 'Агрегатор'],
  ['/navoi', '04', "Navo'i LLM"],
  ['/partnership', '05', 'Партнёрство'],
]

export default function NationalShell({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  return <div className="national-site">
    <nav className="national-topnav">
      <Link href="/" className="national-brand"><span className="national-logo">S</span><strong>Sovable <i>AI</i></strong></Link>
      <div className="national-menu">{nav.map(([href, number, label]) => <Link key={href} href={href} className={router.pathname === href ? 'active' : ''}><small>{number}</small>{label}</Link>)}<a href="https://docs.sovable.ai" target="_blank" rel="noreferrer"><small>06</small>Документация</a></div>
      <div className="national-lang"><button className="active">RU</button><button disabled title="English version is being prepared">EN</button></div>
    </nav>
    {children}
    <footer className="national-footer"><span>© 2026 Solvable AI</span><span>Национальная AI-платформа · <a href="https://docs.sovable.ai" target="_blank" rel="noreferrer">Документация</a></span><span><Link href="/portal">User Portal</Link> · <Link href="/admin">Organization Admin</Link> · <Link href="/creator">Agent Creator</Link></span></footer>
  </div>
}

export function Pager({ previous, previousHref, next, nextHref }: { previous?: string; previousHref?: string; next?: string; nextHref?: string }) {
  return <div className="national-pager"><span>{previous && previousHref && <Link href={previousHref}><small>Назад</small><b>← {previous}</b></Link>}</span>{next && nextHref && <Link href={nextHref} className="next"><small>Далее</small><b>{next} →</b></Link>}</div>
}

export function Eyebrow({ children }: { children: React.ReactNode }) { return <div className="national-eyebrow">{children}</div> }
