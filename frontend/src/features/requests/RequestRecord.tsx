import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowUpRight } from 'lucide-react'
import { CitationChip, ConfidenceMeter, EmptyState, ErrorState, StatusBadge } from '@/design-system/primitives'
import { DecisionTraceDrawer } from '@/features/decisions/DecisionTraceDrawer'
import { cn } from '@/lib/cn'
import { ApiError } from '@/lib/api'
import { approveRequest, escalateRequest, getRequest } from './api'
import type { DecisionOut, MessageOut } from './types'

const TABS = [
  { key: 'conversation', label: 'Conversation', availableFrom: 3 },
  { key: 'ai-decision', label: 'AI Decision', availableFrom: 4 },
  { key: 'evidence', label: 'Evidence', availableFrom: 4 },
  { key: 'workflow', label: 'Workflow', availableFrom: 7 },
  { key: 'audit', label: 'Audit', availableFrom: 8 },
] as const

function MessageBubble({ message }: { message: MessageOut }) {
  const isCustomer = message.author === 'customer'
  return (
    <div className={cn('max-w-[85%] rounded-card border p-3 text-body', isCustomer ? 'border-border bg-surface' : 'ml-auto border-ai-border bg-ai-tint')}>
      <div className="mb-1 text-small font-medium capitalize text-text-muted">{message.author}</div>
      <p className="text-text-primary">{message.body}</p>
    </div>
  )
}

function ConversationTab({ decision, messages }: { decision: DecisionOut | undefined; messages: MessageOut[] }) {
  return (
    <div className="space-y-3">
      {decision && (
        <div className="space-y-2 rounded-card border border-border bg-surface p-3">
          <div className="flex items-center justify-between">
            <span className="text-small font-medium uppercase tracking-wide text-text-muted">Latest AI decision</span>
            <span className="font-mono text-small text-text-muted">{decision.model}</span>
          </div>
          <ConfidenceMeter value={decision.confidence} threshold={decision.threshold} label={decision.type.replace('_', ' ')} />
          {decision.evidence.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {decision.evidence.map((e) => (
                <CitationChip key={e.id} mode={e.retrieval_mode as 'vector' | 'vectorless'} articleId={e.article_ref} locator={e.locator} score={e.score} />
              ))}
            </div>
          )}
        </div>
      )}
      {messages.length === 0 ? <EmptyState headline="No messages yet" /> : messages.map((m) => <MessageBubble key={m.id} message={m} />)}
    </div>
  )
}

function AiDecisionTab({ decision, onViewTrace }: { decision: DecisionOut | undefined; onViewTrace: () => void }) {
  if (!decision) return <EmptyState headline="No AI decision yet" description="This request hasn't been evaluated by the AI pipeline." />
  return (
    <div className="space-y-4">
      <ConfidenceMeter value={decision.confidence} threshold={decision.threshold} label={decision.type.replace('_', ' ')} />
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-small">
        {Object.entries(decision.signals).map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="capitalize text-text-muted">{key.replace('_', ' ')}</dt>
            <dd className="text-right font-mono text-text-primary">{typeof value === 'number' ? `${Math.round(value * 100)}%` : String(value)}</dd>
          </div>
        ))}
      </dl>
      {decision.rule_evaluations.length > 0 && (
        <table className="w-full text-small">
          <thead>
            <tr className="text-left text-text-muted">
              <th className="pb-1 font-medium">Rule</th>
              <th className="pb-1 font-medium">Outcome</th>
              <th className="pb-1 text-right font-medium">Priority</th>
            </tr>
          </thead>
          <tbody>
            {decision.rule_evaluations.map((r) => (
              <tr key={r.rule_code} className="border-t border-border">
                <td className="py-1 font-mono">{r.rule_code}</td>
                <td className="py-1">{r.outcome.replace('_', ' ')}</td>
                <td className="py-1 text-right font-mono">{r.priority}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <button type="button" onClick={onViewTrace} className="flex items-center gap-1 text-small font-medium text-brand hover:underline">
        View full pipeline trace <ArrowUpRight size={14} />
      </button>
    </div>
  )
}

function EvidenceTab({ decision }: { decision: DecisionOut | undefined }) {
  if (!decision || decision.evidence.length === 0) {
    return <EmptyState headline="No evidence" description="This decision didn't cite any knowledge articles." />
  }
  return (
    <div className="space-y-2">
      {decision.evidence.map((e) => (
        <div key={e.id} className="flex items-center justify-between rounded-card border border-border bg-surface p-3">
          <CitationChip mode={e.retrieval_mode as 'vector' | 'vectorless'} articleId={e.article_ref} locator={e.locator} score={e.score} />
          <span className="text-small text-text-muted">{e.version_ref}</span>
        </div>
      ))}
    </div>
  )
}

export interface RequestRecordProps {
  requestId: string;
  onActionComplete?: () => void
}

export function RequestRecord({ requestId, onActionComplete }: RequestRecordProps) {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]['key']>('conversation')
  const [escalating, setEscalating] = useState(false)
  const [reason, setReason] = useState('')
  const [traceDecisionId, setTraceDecisionId] = useState<string | null>(null)

  const { data: request, isLoading, error, refetch } = useQuery({
    queryKey: ['request', requestId],
    queryFn: () => getRequest(requestId),
  })

  const approveMutation = useMutation({
    mutationFn: () => approveRequest(requestId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['requests'] })
      queryClient.invalidateQueries({ queryKey: ['request', requestId] })
      onActionComplete?.()
    },
  })

  const escalateMutation = useMutation({
    mutationFn: () => escalateRequest(requestId, reason || 'Escalated by agent'),
    onSuccess: () => {
      setEscalating(false)
      setReason('')
      queryClient.invalidateQueries({ queryKey: ['requests'] })
      queryClient.invalidateQueries({ queryKey: ['request', requestId] })
      onActionComplete?.()
    },
  })

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      const typing = document.activeElement instanceof HTMLInputElement || document.activeElement instanceof HTMLTextAreaElement
      if (typing || escalating) return
      if (e.key === 'a' || e.key === 'A') { e.preventDefault(); approveMutation.mutate() }
      else if (e.key === 'e' || e.key === 'E') { e.preventDefault(); setEscalating(true) }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [escalating, approveMutation])

  if (isLoading) return <div className="p-6 text-text-muted">Loading…</div>

  if (error) {
    return (
      <ErrorState
        message={error instanceof ApiError ? error.message : 'Could not load this request.'}
        traceId={error instanceof ApiError ? (error.traceId ?? undefined) : undefined}
        onRetry={() => refetch()}
      />
    )
  }

  if (!request) return null

  const latestDecision = request.decisions.at(-1)
  const heldRule = latestDecision?.rule_overridden ? latestDecision.rule_evaluations[0] : undefined

  return (
    <div className="flex h-full flex-col" data-request-record>
      <div className="border-b border-border p-4">
        <div className="mb-1 flex items-center gap-2">
          <span className="font-mono text-small text-text-muted">{request.reference}</span>
          <StatusBadge variant="neutral" label={request.status.replace('_', ' ')} />
        </div>
        <h2 className="text-h1 font-semibold text-text-primary">{request.customer.full_name}</h2>
        <p className="text-small text-text-secondary">
          {request.category ?? 'Uncategorized'} {request.intent ? `· ${request.intent}` : ''} · {request.channel}
        </p>
      </div>

      <div className="flex border-b border-border px-4">
        {TABS.map((tab) => {
          const available = tab.availableFrom <= 4
          return (
            <button
              key={tab.key}
              type="button"
              disabled={!available}
              title={available ? undefined : `Lands in increment ${tab.availableFrom}`}
              onClick={() => available && setActiveTab(tab.key)}
              className={cn(
                'border-b-2 px-3 py-2 text-small font-medium',
                available ? 'text-text-secondary hover:text-text-primary' : 'cursor-not-allowed text-text-muted opacity-50',
                activeTab === tab.key && available ? 'border-brand text-brand' : 'border-transparent',
              )}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      <div className="scroller flex-1 space-y-3 overflow-y-auto p-4">
        {heldRule && (
          <div className="flex items-center gap-2 rounded-card border border-ai-border bg-ai-tint p-3 text-small text-ai">
            <AlertTriangle size={16} />
            Held for review — rule <span className="font-mono">{heldRule.rule_code}</span> overrides the AI decision.
          </div>
        )}
        {activeTab === 'conversation' && <ConversationTab decision={latestDecision} messages={request.messages} />}
        {activeTab === 'ai-decision' && <AiDecisionTab decision={latestDecision} onViewTrace={() => latestDecision && setTraceDecisionId(latestDecision.id)} />}
        {activeTab === 'evidence' && <EvidenceTab decision={latestDecision} />}
      </div>

      <div className="border-t border-border p-4">
        {escalating ? (
          <div className="space-y-2">
            <textarea
              autoFocus
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Reason for escalation…"
              className="h-16 w-full rounded-control border border-border-strong p-2 text-body outline-none focus:border-brand"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => escalateMutation.mutate()}
                disabled={escalateMutation.isPending}
                className="h-8 rounded-control bg-danger px-3 text-small font-medium text-white hover:bg-danger-hover disabled:opacity-60"
              >
                Confirm escalate
              </button>
              <button type="button" onClick={() => setEscalating(false)} className="h-8 rounded-control border border-border-strong px-3 text-small">
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending}
              className="h-8 rounded-control bg-success px-3 text-small font-medium text-white hover:opacity-90 disabled:opacity-60"
            >
              Approve <span className="opacity-70">(A)</span>
            </button>
            <button
              type="button"
              onClick={() => setEscalating(true)}
              className="h-8 rounded-control border border-danger-border bg-danger-tint px-3 text-small font-medium text-danger hover:bg-danger hover:text-white"
            >
              Escalate <span className="opacity-70">(E)</span>
            </button>
          </div>
        )}
        {(approveMutation.isError || escalateMutation.isError) && (
          <p className="mt-2 text-small text-danger">
            {(approveMutation.error instanceof ApiError && approveMutation.error.message) ||
              (escalateMutation.error instanceof ApiError && escalateMutation.error.message) ||
              'Action failed.'}
          </p>
        )}
      </div>

      <DecisionTraceDrawer decisionId={traceDecisionId} onClose={() => setTraceDecisionId(null)} />
    </div>
  )
}
