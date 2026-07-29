import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RotateCcw } from 'lucide-react'
import { StatusBadge, type BadgeVariant } from '@/design-system/primitives'
import { listWorkflowRuns, retryWorkflowAction } from './api'
import type { WorkflowRunOut } from './types'

const RUN_VARIANT: Record<WorkflowRunOut['status'], BadgeVariant> = {
  running: 'brand',
  succeeded: 'success',
  failed: 'danger',
}

export function WorkflowRunsPanel() {
  const queryClient = useQueryClient()
  const { data: runs } = useQuery({ queryKey: ['workflow-runs'], queryFn: listWorkflowRuns })

  const retryMutation = useMutation({
    mutationFn: ({ runId, actionId }: { runId: string; actionId: string }) => retryWorkflowAction(runId, actionId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['workflow-runs'] }),
  })

  return (
    <div className="rounded-card border border-border bg-surface p-4">
      <h2 className="mb-2 text-h2 font-semibold text-text-primary">Recent runs</h2>
      <div className="space-y-2">
        {runs?.map((run) => (
          <div key={run.id} className="rounded-control border border-border p-3">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-mono text-small">{run.workflow_key}</span>
              <StatusBadge variant={RUN_VARIANT[run.status]} label={run.status} />
            </div>
            <div className="space-y-1">
              {run.actions.map((action) => (
                <div key={action.id} className="flex items-center justify-between text-small">
                  <span className="text-text-secondary">
                    {action.action_type}
                    {action.error_message && <span className="text-danger"> — {action.error_message}</span>}
                  </span>
                  {action.status === 'failed' && (
                    <button
                      type="button"
                      onClick={() => retryMutation.mutate({ runId: run.id, actionId: action.id })}
                      disabled={retryMutation.isPending}
                      className="flex h-6 items-center gap-1 rounded-control border border-border-strong px-2 text-small hover:bg-surface-sunken disabled:opacity-60"
                    >
                      <RotateCcw size={11} /> Retry
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
