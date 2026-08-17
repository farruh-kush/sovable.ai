const steps = [
  { icon: '▤', title: 'Request', body: 'Intake and validate user request' },
  { icon: '◉', title: 'Masking', body: 'PII detection and secure masking' },
  { icon: '⇄', title: 'Routing', body: 'Policy-based routing to sovereign core' },
  { icon: '▣', title: 'Restore', body: 'De-mask authorized fields only' },
  { icon: '➤', title: 'Response', body: 'Return secure response' },
]

export default function DataGovernancePipeline() {
  return (
    <section className="governance-pipeline" aria-labelledby="governance-pipeline-title">
      <div className="governance-pipeline-heading">
        <span className="governance-rule" />
        <div className="governance-pipeline-title-wrap">
          <span className="eyebrow" id="governance-pipeline-title">DATA GOVERNANCE PIPELINE</span>
          <span className="governance-lock" aria-hidden="true">♙</span>
        </div>
        <span className="governance-rule" />
      </div>
      <div className="governance-pipeline-row">
        {steps.map((step, index) => (
          <>
            <div key={step.title} className="governance-step">
              <span className="governance-step-icon" aria-hidden="true">{step.icon}</span>
              <div>
                <strong>{step.title}</strong>
                <small>{step.body}</small>
              </div>
            </div>
            {index < steps.length - 1 && <span className="governance-arrow" aria-hidden="true">→</span>}
          </>
        ))}
      </div>
    </section>
  )
}
