import { ConfigResourceListPage } from './ConfigResourceListPage'
import { RuleSimulatorPanel } from './RuleSimulatorPanel'

export function BusinessRulesPage() {
  return (
    <ConfigResourceListPage
      kind="business_rule"
      module="business_rules"
      title="Business rules"
      description="WHEN/THEN rules that can override the AI's decision — the single most important safety mechanism in the product."
      configPlaceholder={'{\n  "when": {"category": "Legal"},\n  "then": {"outcome": "require_human", "priority": 10}\n}'}
      extra={<RuleSimulatorPanel />}
    />
  )
}
