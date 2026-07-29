import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { createDraft } from './api'
import type { ConfigResourceKind } from './types'

export interface CreateDraftFormProps {
  kind: ConfigResourceKind
  open: boolean
  onClose: () => void
  configPlaceholder: string
}

/**
 * Config is edited as raw JSON — a deliberate simplification. §10 calls for bespoke
 * editors per kind (RuleBuilder, WorkflowCanvas, PromptEditor+diff, routing matrix grid);
 * building four visual editors was out of scope for this pass. The backend's lifecycle
 * (draft → simulate → publish → rollback) is real regardless of how the config was typed in.
 */
export function CreateDraftForm({ kind, open, onClose, configPlaceholder }: CreateDraftFormProps) {
  const queryClient = useQueryClient()
  const [key, setKey] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [configText, setConfigText] = useState(configPlaceholder)
  const [jsonError, setJsonError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => createDraft(kind, { key, name, description: description || undefined, config: JSON.parse(configText) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['automation-current', kind] })
      setKey('')
      setName('')
      setDescription('')
      setConfigText(configPlaceholder)
      onClose()
    },
  })

  if (!open) return null

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      JSON.parse(configText)
      setJsonError(null)
      mutation.mutate()
    } catch {
      setJsonError('Config must be valid JSON.')
    }
  }

  return (
    <Modal onClose={onClose} title="New draft version">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-small text-text-secondary">Key</label>
          <input
            required
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="e.g. BR-045"
            className="h-8 w-full rounded-control border border-border-strong px-2.5 font-mono text-body outline-none focus:border-brand"
          />
        </div>
        <div>
          <label className="mb-1 block text-small text-text-secondary">Name</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand"
          />
        </div>
        <div>
          <label className="mb-1 block text-small text-text-secondary">Description</label>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand"
          />
        </div>
        <div>
          <label className="mb-1 block text-small text-text-secondary">Config (JSON)</label>
          <textarea
            required
            value={configText}
            onChange={(e) => setConfigText(e.target.value)}
            rows={8}
            className="w-full rounded-control border border-border-strong p-2.5 font-mono text-small outline-none focus:border-brand"
          />
          {jsonError && <p className="mt-1 text-small text-danger">{jsonError}</p>}
        </div>
        {mutation.isError && (
          <p className="text-small text-danger">{mutation.error instanceof ApiError ? mutation.error.message : 'Could not save this draft.'}</p>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="h-8 rounded-control border border-border-strong px-3 text-small">
            Cancel
          </button>
          <button type="submit" disabled={mutation.isPending} className="h-8 rounded-control bg-brand px-3 text-small font-medium text-white hover:bg-brand-hover disabled:opacity-60">
            {mutation.isPending ? 'Saving…' : 'Save as draft'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
