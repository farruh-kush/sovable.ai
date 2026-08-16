import Link from 'next/link'
import { useRouter } from 'next/router'
import { useLocale, Locale } from '../lib/locale'

const nav = [
  ['/', '01', 'nav.overview'],
  ['/app-store', '02', 'nav.appstore'],
  ['/aggregator', '03', 'nav.aggregator'],
  ['/navoi', '04', 'nav.navoi'],
  ['/partnership', '05', 'nav.partnership'],
]

export default function NationalShell({ children }: { children: React.ReactNode }) {
  const router = useRouter(); const { locale, setLocale, t } = useLocale()
  return <div className="national-site"><nav className="national-topnav"><Link href="/" className="national-brand"><span className="national-logo">S</span><strong>Sovable <i>AI</i></strong></Link><div className="national-menu">{nav.map(([href, number, key]) => <Link key={href} href={href} className={router.pathname === href ? 'active' : ''}><small>{number}</small>{t(key)}</Link>)}<Link href="/documentation" className={router.pathname === '/documentation' ? 'active' : ''}><small>06</small>{t('nav.documentation')}</Link></div><div className="national-lang">{(['uz','ru','en'] as Locale[]).map(code => <button key={code} className={locale === code ? 'active' : ''} onClick={() => setLocale(code)}>{t(`common.${code}`)}</button>)}</div></nav>{children}<footer className="national-footer"><span>© 2026 Solvable AI</span><span>{t('home.eyebrow').split(' · ')[0]} · <Link href="/documentation">{t('common.docs')}</Link></span><span><Link href="/portal">{t('common.userPortal')}</Link> · <Link href="/admin">{t('common.orgAdmin')}</Link> · <Link href="/creator">{t('common.creator')}</Link></span></footer></div>
}

export function Pager({ previous, previousHref, next, nextHref }: { previous?: string; previousHref?: string; next?: string; nextHref?: string }) {
  const { t } = useLocale(); return <div className="national-pager"><span>{previous && previousHref && <Link href={previousHref}><small>{t('common.back')}</small><b>← {previous}</b></Link>}</span>{next && nextHref && <Link href={nextHref} className="next"><small>{t('common.next')}</small><b>{next} →</b></Link>}</div>
}
export function Eyebrow({ children }: { children: React.ReactNode }) { return <div className="national-eyebrow">{children}</div> }
