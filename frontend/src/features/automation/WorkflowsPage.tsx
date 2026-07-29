import { ConfigResourceListPage } from './ConfigResourceListPage'
import { WorkflowRunsPanel } from './WorkflowRunsPanel'

export function WorkflowsPage() {
  return (
    <ConfigResourceListPage
      kind="workflow"
      module="workflow_builder"
      title="Workflows"
      description="Definitions that fire actions after an AI decision — notifications, approval tasks, webhooks."
      configPlaceholder={'{\n  "nodes": [{"id": "n1", "type": "trigger", "on": "decision.hold"}],\n  "edges": []\n}'}
      extra={<WorkflowRunsPanel />}
    />
  )
}
