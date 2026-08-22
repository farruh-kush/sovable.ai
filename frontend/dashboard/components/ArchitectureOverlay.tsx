import { useEffect, useState } from 'react'

type Point = { x: number; y: number }
type Layout = {
  models: Point[]
  coreLeft: Point[]
  coreRight: Point[]
  platformLeft: Point[]
  platformRight: Point[]
  users: Point[]
  modelBus: number
  userBus: number
}

function edge(node: Element, root: DOMRect, side: 'left' | 'right'): Point {
  const rect = node.getBoundingClientRect()
  return {
    x: (side === 'left' ? rect.left : rect.right) - root.left,
    y: rect.top + rect.height / 2 - root.top,
  }
}

export default function ArchitectureOverlay() {
  const [layout, setLayout] = useState<Layout | null>(null)

  useEffect(() => {
    const measure = () => {
      const root = document.querySelector('.national-architecture')
      if (!root || window.innerWidth <= 1200) {
        setLayout(null)
        return
      }
      const rootRect = root.getBoundingClientRect()
      const nodes = (selector: string, side: 'left' | 'right') =>
        Array.from(document.querySelectorAll(selector)).map((node) => edge(node, rootRect, side))
      const models = nodes('.national-architecture > .national-column:first-child > .national-node', 'right')
      const coreLeft = nodes('.national-architecture > .core-column > .national-node', 'left')
      const coreRight = nodes('.national-architecture > .core-column > .national-node', 'right')
      const platformLeft = nodes('.national-architecture > .platform-column > .national-node', 'left')
      const platformRight = nodes('.national-architecture > .platform-column > .national-node', 'right')
      const users = nodes('.national-architecture > .audience-column > .national-node', 'left')
      if (models.length !== 3 || coreLeft.length !== 2 || coreRight.length !== 2 || platformLeft.length !== 2 || platformRight.length !== 2 || users.length !== 3) {
        setLayout(null)
        return
      }
      const modelConnector = document.querySelector('.national-architecture > .national-connectors:nth-child(2)')
      const userConnector = document.querySelector('.national-architecture > .national-connectors:nth-child(6)')
      const modelRect = modelConnector?.getBoundingClientRect()
      const userRect = userConnector?.getBoundingClientRect()
      setLayout({
        models,
        coreLeft,
        coreRight,
        platformLeft,
        platformRight,
        users,
        modelBus: modelRect ? modelRect.left + modelRect.width / 2 - rootRect.left : (models[0].x + coreLeft[0].x) / 2,
        userBus: userRect ? userRect.left + userRect.width / 2 - rootRect.left : (platformRight[0].x + users[0].x) / 2,
      })
    }
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(document.body)
    window.addEventListener('resize', measure)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', measure)
    }
  }, [])

  if (!layout) return null
  const { models, coreLeft, coreRight, platformLeft, platformRight, users, modelBus, userBus } = layout
  const gold = '#c9992e'
  const slate = '#aeb9ca'
  const wire = { fill: 'none', strokeWidth: 3, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }
  const dot = (point: Point, color: string, key: string) => (
    <circle key={key} cx={point.x} cy={point.y} r={5} fill={color} stroke="#fff" strokeWidth={2} />
  )
  const modelBusTop = Math.min(...models.map((point) => point.y), ...coreLeft.map((point) => point.y))
  const modelBusBottom = Math.max(...models.map((point) => point.y), ...coreLeft.map((point) => point.y))
  const userBusTop = Math.min(...platformRight.map((point) => point.y), ...users.map((point) => point.y))
  const userBusBottom = Math.max(...platformRight.map((point) => point.y), ...users.map((point) => point.y))

  return (
    <svg className="architecture-overlay" aria-hidden="true">
      <path d={`M ${modelBus} ${modelBusTop} V ${modelBusBottom}`} stroke={slate} {...wire} />
      {models.map((point, index) => (
        <g key={`model-link-${index}`}>
          <path d={`M ${point.x} ${point.y} H ${modelBus}`} stroke={slate} {...wire} />
          {dot(point, slate, `model-dot-${index}`)}
        </g>
      ))}
      {coreLeft.map((point, index) => (
        <g key={`core-left-link-${index}`}>
          <path d={`M ${modelBus} ${point.y} H ${point.x}`} stroke={gold} {...wire} />
          {dot(point, gold, `core-left-${index}`)}
        </g>
      ))}
      <circle cx={modelBus} cy={modelBusTop} r={5} fill={slate} stroke="#fff" strokeWidth={2} />
      <circle cx={modelBus} cy={modelBusBottom} r={5} fill={gold} stroke="#fff" strokeWidth={2} />
      <path d={`M ${coreRight[0].x} ${coreRight[0].y} H ${platformLeft[0].x}`} stroke={gold} {...wire} />
      <path d={`M ${coreRight[1].x} ${coreRight[1].y} H ${platformLeft[1].x}`} stroke={gold} {...wire} />
      {coreRight.map((point, index) => dot(point, gold, `core-right-${index}`))}
      {platformLeft.map((point, index) => dot(point, gold, `platform-left-${index}`))}
      <path d={`M ${userBus} ${userBusTop} V ${userBusBottom}`} stroke={gold} {...wire} />
      {platformRight.map((point, index) => (
        <g key={`platform-right-link-${index}`}>
          <path d={`M ${point.x} ${point.y} H ${userBus}`} stroke={gold} {...wire} />
          {dot(point, gold, `platform-right-${index}`)}
        </g>
      ))}
      {users.map((point, index) => (
        <g key={`user-link-${index}`}>
          <path d={`M ${userBus} ${point.y} H ${point.x}`} stroke={gold} {...wire} />
          {dot(point, gold, `user-dot-${index}`)}
        </g>
      ))}
      <circle cx={userBus} cy={userBusTop} r={5} fill={gold} stroke="#fff" strokeWidth={2} />
      <circle cx={userBus} cy={userBusBottom} r={5} fill={gold} stroke="#fff" strokeWidth={2} />
    </svg>
  )
}
