import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Star } from 'lucide-react'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { submitPortalFeedback, trackPortalRequest } from './api'

const STAGES = ['Received', 'Reviewed', 'Preparing answer', 'Resolved']

function ProgressTracker({ current }: { current: string }) {
  const currentIndex = STAGES.indexOf(current)
  return (
    <div className="flex items-center">
      {STAGES.map((stage, i) => (
        <div key={stage} className="flex flex-1 items-center">
          <div className={cn('grid h-7 w-7 shrink-0 place-items-center rounded-full text-small font-medium', i <= currentIndex ? 'bg-brand text-white' : 'bg-surface-sunken text-text-muted')}>
            {i + 1}
          </div>
          {i < STAGES.length - 1 && <div className={cn('mx-1 h-0.5 flex-1', i < currentIndex ? 'bg-brand' : 'bg-surface-sunken')} />}
        </div>
      ))}
    </div>
  )
}

function FeedbackForm({ reference, email }: { reference: string; email: string }) {
  const [rating, setRating] = useState(0)
  const mutation = useMutation({ mutationFn: () => submitPortalFeedback(reference, email, rating) })

  if (mutation.isSuccess) return <p className="text-small text-success">Thanks for the feedback!</p>

  return (
    <div className="mt-3 border-t border-border pt-3">
      <p className="mb-2 text-small text-text-secondary">How did we do?</p>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} type="button" onClick={() => setRating(n)} aria-label={`${n} stars`}>
            <Star size={22} className={n <= rating ? 'fill-warning text-warning' : 'text-border-strong'} />
          </button>
        ))}
      </div>
      {rating > 0 && (
        <button type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending} className="mt-2 h-8 rounded-control bg-brand px-3 text-small font-medium text-white hover:bg-brand-hover disabled:opacity-60">
          Submit rating
        </button>
      )}
    </div>
  )
}

export function TrackPage() {
  const [reference, setReference] = useState('')
  const [email, setEmail] = useState('')

  const mutation = useMutation({ mutationFn: () => trackPortalRequest(reference, email) })

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-display font-bold text-text-primary">Track your request</h1>
        <p className="mt-1 text-body text-text-secondary">Enter your reference number and the email you submitted with.</p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
        className="flex gap-2"
      >
        <input required value={reference} onChange={(e) => setReference(e.target.value)} placeholder="REQ-XXXXXXXX" className="h-9 flex-1 rounded-control border border-border-strong px-2.5 font-mono text-body outline-none focus:border-brand" />
        <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="h-9 flex-1 rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand" />
        <button type="submit" disabled={mutation.isPending} className="h-9 shrink-0 rounded-control bg-brand px-4 text-small font-medium text-white hover:bg-brand-hover disabled:opacity-60">
          Track
        </button>
      </form>

      {mutation.isError && (
        <p className="text-small text-danger">{mutation.error instanceof ApiError ? mutation.error.message : 'Could not find that request.'}</p>
      )}

      {mutation.data && (
        <div className="rounded-card border border-border bg-surface p-4">
          <div className="mb-4 flex items-center justify-between">
            <span className="font-mono text-small text-text-muted">{mutation.data.reference}</span>
            <span className="text-small font-medium text-text-primary">{mutation.data.progress_stage}</span>
          </div>
          <ProgressTracker current={mutation.data.progress_stage} />

          <div className="mt-4 space-y-2">
            {mutation.data.messages.map((m, i) => (
              <div key={i} className={cn('max-w-[85%] rounded-control border p-2.5 text-small', m.author === 'customer' ? 'border-border bg-canvas' : 'ml-auto border-ai-border bg-ai-tint')}>
                {m.body}
              </div>
            ))}
          </div>

          {mutation.data.progress_stage === 'Resolved' && <FeedbackForm reference={mutation.data.reference} email={email} />}
        </div>
      )}
    </div>
  )
}
