import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ErrorState } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import { listSettings, updateSetting } from './api'

function SettingCard({ settingKey, value }: { settingKey: string; value: Record<string, unknown> }) {
  const queryClient = useQueryClient()
  const [text, setText] = useState(JSON.stringify(value, null, 2))
  const [jsonError, setJsonError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => updateSetting(settingKey, JSON.parse(text)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['settings'] }),
  })

  function handleSave() {
    try {
      JSON.parse(text)
      setJsonError(null)
      mutation.mutate()
    } catch {
      setJsonError('Must be valid JSON.')
    }
  }

  return (
    <div className="rounded-card border border-border bg-surface p-4">
      <h3 className="mb-2 font-mono text-h2 font-semibold text-text-primary">{settingKey}</h3>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={7}
        className="w-full rounded-control border border-border-strong p-2.5 font-mono text-small outline-none focus:border-brand"
      />
      {jsonError && <p className="mt-1 text-small text-danger">{jsonError}</p>}
      {mutation.isError && <p className="mt-1 text-small text-danger">{mutation.error instanceof ApiError ? mutation.error.message : 'Could not save.'}</p>}
      <button
        type="button"
        onClick={handleSave}
        disabled={mutation.isPending}
        className="mt-2 h-8 rounded-control bg-brand px-3 text-small font-medium text-white hover:bg-brand-hover disabled:opacity-60"
      >
        {mutation.isPending ? 'Saving…' : 'Save'}
      </button>
    </div>
  )
}

export function SettingsPage() {
  const { data: settings, isLoading, error, refetch } = useQuery({ queryKey: ['settings'], queryFn: listSettings })

  if (error) {
    return <ErrorState message={error instanceof ApiError ? error.message : 'Could not load settings.'} onRetry={() => refetch()} />
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-display font-bold text-text-primary">Settings</h1>
        <p className="mt-1 text-body text-text-secondary">AI provider config and retrieval tuning knobs. Edited as raw JSON — see task doc for why.</p>
      </div>

      {isLoading && <div className="text-text-muted">Loading…</div>}

      <div className="grid grid-cols-2 gap-4">
        {settings?.map((s) => (
          <SettingCard key={s.key} settingKey={s.key} value={s.value} />
        ))}
      </div>
    </div>
  )
}
