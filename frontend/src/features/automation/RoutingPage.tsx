import { ConfigResourceListPage } from './ConfigResourceListPage'

export function RoutingPage() {
  return (
    <ConfigResourceListPage
      kind="routing_rule"
      module="routing_config"
      title="Department routing"
      description="Intent-to-department mappings and escalation rules that decide where a request lands when it isn't auto-answered."
      configPlaceholder={'{\n  "intent": "dispute_charge",\n  "department": "Cards & Payments"\n}'}
    />
  )
}
