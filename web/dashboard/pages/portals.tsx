import Link from 'next/link'

const portals = [
  { tone: 'user', code: '01', label: 'USER PORTAL', title: 'Build with governed AI', text: 'Use the unified API, playground, model catalog, usage controls, privacy tools, and installed agents from one workspace.', href: '/portal', action: 'Open User Portal', register: '/portal/register' },
  { tone: 'admin', code: '02', label: 'ORGANIZATION ADMIN', title: 'Operate your AI estate', text: 'Govern members, provider access, routing policies, budgets, billing, agents, and audit evidence for your organization.', href: '/admin', action: 'Open Admin Portal', register: '/admin/register' },
  { tone: 'controller', code: '03', label: 'PLATFORM ADMIN', title: 'Control the control plane', text: 'Manage platform-wide provider health, routing reliability, model catalog, pricing, and operational safeguards.', href: '/controller', action: 'Enter Platform Controller', register: null },
  { tone: 'creator', code: '04', label: 'AGENT CREATOR', title: 'Publish trusted agents', text: 'Package, test, review, release, and monetize agents through a governed marketplace with clear permissions.', href: '/creator', action: 'Explore Marketplace', register: '/creator/register' },
]

export default function Portals() {
  return <main className="portal-directory-page">
    <header className="portal-directory-header"><Link href="/" className="brand"><span className="brand-mark">S</span><span>Solvable <em>AI</em></span></Link><Link href="/" className="text-link">Back to sovable.ai</Link></header>
    <section className="portal-directory-hero"><span className="eyebrow">ONE PLATFORM · FOUR PURPOSE-BUILT SURFACES</span><h1>Choose the way you operate with Solvable.</h1><p>Every role enters through a clear boundary. Use AI, govern an organization, operate the platform, or create the next trusted agent.</p></section>
    <section className="portal-directory-grid">{portals.map(portal => <article className={`portal-directory-card portal-tone-${portal.tone}`} key={portal.code}><div className="portal-card-top"><span className="portal-code">{portal.code}</span><span className="eyebrow">{portal.label}</span></div><h2>{portal.title}</h2><p>{portal.text}</p><div className="portal-card-actions"><Link href={portal.href} className="button primary">{portal.action}</Link>{portal.register && <Link href={portal.register} className="text-link">Register →</Link>}</div></article>)}</section>
    <section className="portal-directory-note"><span className="eyebrow">BOUNDARIES BY DESIGN</span><p>The Platform Controller is never self-registered. Organization Admins govern their tenant. Users work inside the tenant. Agent Creators publish through review before an agent can become installable.</p></section>
  </main>
}
