import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { ApiError } from '@/lib/api'
import { submitPortalRequest } from './api'

export function SubmitPage() {
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')

  const mutation = useMutation({
    mutationFn: () => submitPortalRequest({ customer_email: email, customer_name: name, subject, body }),
  })

  if (mutation.data) {
    const result = mutation.data
    return (
      <div className="rounded-card border border-success-border bg-success-tint p-6 text-center">
        <h1 className="text-h1 font-semibold text-text-primary">Thanks — we've got it.</h1>
        <p className="mt-2 text-body text-text-secondary">
          Your reference number is <span className="font-mono font-semibold text-text-primary">{result.reference}</span>. Save this to track your request.
        </p>
        {result.ai_message && (
          <div className="mt-4 rounded-control border border-border bg-surface p-4 text-left">
            <p className="text-body text-text-primary">{result.ai_message}</p>
            {result.citations.length > 0 && (
              <p className="mt-2 text-small text-text-muted">Sources: {result.citations.join(', ')}</p>
            )}
          </div>
        )}
        <Link to="/portal/track" className="mt-4 inline-block text-small font-medium text-brand hover:underline">
          Track this request →
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-display font-bold text-text-primary">Submit a request</h1>
        <p className="mt-1 text-body text-text-secondary">Tell us what's going on and we'll get you an answer as fast as possible.</p>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
        className="space-y-3 rounded-card border border-border bg-surface p-4"
      >
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-small text-text-secondary">Your name</label>
            <input required value={name} onChange={(e) => setName(e.target.value)} className="h-9 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand" />
          </div>
          <div>
            <label className="mb-1 block text-small text-text-secondary">Email</label>
            <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="h-9 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand" />
          </div>
        </div>
        <div>
          <label className="mb-1 block text-small text-text-secondary">Subject</label>
          <input required value={subject} onChange={(e) => setSubject(e.target.value)} className="h-9 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand" />
        </div>
        <div>
          <label className="mb-1 block text-small text-text-secondary">Describe your request</label>
          <textarea required value={body} onChange={(e) => setBody(e.target.value)} rows={5} className="w-full rounded-control border border-border-strong p-2.5 text-body outline-none focus:border-brand" />
        </div>
        {mutation.isError && <p className="text-small text-danger">{mutation.error instanceof ApiError ? mutation.error.message : 'Could not submit your request — please try again.'}</p>}
        <button type="submit" disabled={mutation.isPending} className="h-9 rounded-control bg-brand px-4 text-small font-medium text-white hover:bg-brand-hover disabled:opacity-60">
          {mutation.isPending ? 'Submitting…' : 'Submit request'}
        </button>
      </form>
    </div>
  )
}
