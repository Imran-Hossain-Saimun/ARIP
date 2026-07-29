import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from '@/design-system/primitives'
import { ingestKnowledge } from './api'
import { listDepartments } from '@/features/reference/api'
import { ApiError } from '@/lib/api'
import type { AccessLevel } from './types'

export interface IngestArticleFormProps {
  open: boolean
  onClose: () => void
}

/**
 * Single-page ingestion form — simplified vs. §10's 4-step IngestionWizard
 * (FileDropzone/DuplicateWarning/MetadataForm/ReviewerPicker/IndexProgress). Real file
 * upload + text extraction for PDF/DOCX isn't implemented (see backend/app/knowledge/
 * router.py docstring) — this form takes pasted text directly, which covers the same
 * ingest → chunk → embed pipeline without the missing parser dependency.
 */
export function IngestArticleForm({ open, onClose }: IngestArticleFormProps) {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [category, setCategory] = useState('')
  const [accessLevel, setAccessLevel] = useState<AccessLevel>('internal')
  const [content, setContent] = useState('')

  const { data: departments } = useQuery({ queryKey: ['departments'], queryFn: listDepartments })

  const mutation = useMutation({
    mutationFn: () => ingestKnowledge({ title, department_id: departmentId || undefined, category: category || undefined, access_level: accessLevel, content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge'] })
      setTitle('')
      setCategory('')
      setContent('')
      onClose()
    },
  })

  if (!open) return null

  return (
    <Modal onClose={onClose} title="Add knowledge article">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <div>
          <label className="mb-1 block text-small text-text-secondary">Title</label>
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-small text-text-secondary">Department</label>
            <select
              value={departmentId}
              onChange={(e) => setDepartmentId(e.target.value)}
              className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand"
            >
              <option value="">—</option>
              {departments?.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-small text-text-secondary">Access level</label>
            <select
              value={accessLevel}
              onChange={(e) => setAccessLevel(e.target.value as AccessLevel)}
              className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand"
            >
              <option value="public">Public</option>
              <option value="internal">Internal</option>
              <option value="restricted">Restricted</option>
            </select>
          </div>
        </div>
        <div>
          <label className="mb-1 block text-small text-text-secondary">Category</label>
          <input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand"
          />
        </div>
        <div>
          <label className="mb-1 block text-small text-text-secondary">Content (markdown headings become sections)</label>
          <textarea
            required
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={8}
            className="w-full rounded-control border border-border-strong p-2.5 font-mono text-small outline-none focus:border-brand"
          />
        </div>
        {mutation.isError && (
          <p className="text-small text-danger">{mutation.error instanceof ApiError ? mutation.error.message : 'Could not save this article.'}</p>
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
