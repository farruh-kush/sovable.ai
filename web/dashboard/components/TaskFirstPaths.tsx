import Link from 'next/link'
import { trackEvent } from '../lib/analytics'

type TaskPath = {
  number: string
  tone: string
  icon: string
  label: string
  title: string
  text: string
  action: string
  href: string
  event: string
}

const paths: TaskPath[] = [
  {
    number: '01',
    tone: 'gold',
    icon: '✦',
    label: 'USE AN AI AGENT',
    title: 'Find a ready-to-use agent',
    text: 'Start with a governed AI application for a ministry, industry, or company workflow.',
    action: 'Open AI App Store',
    href: '/app-store',
    event: 'task_use_agent',
  },
  {
    number: '02',
    tone: 'green',
    icon: '⌁',
    label: 'ROUTE AN API REQUEST',
    title: 'Test the AI router',
    text: 'Inspect masking, routing reasons, provider health, latency, and cost in one protected flow.',
    action: 'Explore Aggregator',
    href: '/aggregator',
    event: 'task_route_api',
  },
  {
    number: '03',
    tone: 'navy',
    icon: '+',
    label: 'CREATE AN AGENT',
    title: 'Publish into the App Store',
    text: 'Build a governed agent with permissions, review evidence, supported languages, and release controls.',
    action: 'Open Creator Portal',
    href: '/creator/login?next=%2Fcreator',
    event: 'task_create_agent',
  },
  {
    number: '04',
    tone: 'purple',
    icon: '⌂',
    label: 'MANAGE AN ORGANIZATION',
    title: 'Control people, policy, and spend',
    text: 'Give an organization administrator one place for members, budgets, providers, and audit activity.',
    action: 'Open Admin Portal',
    href: '/admin/login?next=%2Fadmin',
    event: 'task_manage_org',
  },
]

export default function TaskFirstPaths() {
  return (
    <section className="task-first" aria-labelledby="task-first-title">
      <div className="task-first-heading">
        <div>
          <div className="national-eyebrow">
            START WITH A JOB TO BE DONE
          </div>
          <h2 id="task-first-title">What do you want to do?</h2>
        </div>
        <p>
          Choose a path first. Explore the architecture when you need the proof
          behind the platform.
        </p>
      </div>
      <div className="task-first-grid">
        {paths.map(path => (
          <Link
            href={path.href}
            key={path.number}
            className={`task-path-card ${path.tone}`}
            data-analytics-event={path.event}
            onClick={() => trackEvent(path.event, { href: path.href })}
          >
            <div className="task-path-top">
              <span>{path.number}</span>
              <i aria-hidden="true">{path.icon}</i>
            </div>
            <div className="task-path-label">{path.label}</div>
            <h3>{path.title}</h3>
            <p>{path.text}</p>
            <strong>{path.action} <b aria-hidden="true">→</b></strong>
          </Link>
        ))}
      </div>
    </section>
  )
}
