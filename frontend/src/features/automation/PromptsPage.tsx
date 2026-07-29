import { ConfigResourceListPage } from './ConfigResourceListPage'

export function PromptsPage() {
  return (
    <ConfigResourceListPage
      kind="prompt_template"
      module="prompt_management"
      title="Prompts"
      description="Templates the AI service uses to generate draft/auto replies. Versioned, approvable, rollback-able."
      configPlaceholder={'{\n  "model": "claude-sonnet-4.6",\n  "text": "Answer using only the provided citations."\n}'}
    />
  )
}
