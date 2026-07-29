import { api } from '@/lib/api'
import type { MailboxOut, ParseFailureOut, SyncResult } from './types'

export function listMailboxes() {
  return api.get<MailboxOut[]>('/v1/email/mailboxes')
}

export function syncMailbox(id: string) {
  return api.post<SyncResult>(`/v1/email/mailboxes/${id}/sync`, undefined)
}

export function listParseFailures(resolved?: boolean) {
  const qs = resolved === undefined ? '' : `?resolved=${resolved}`
  return api.get<ParseFailureOut[]>(`/v1/email/parse-failures${qs}`)
}

export function resolveParseFailure(id: string) {
  return api.post<ParseFailureOut>(`/v1/email/parse-failures/${id}/resolve`, undefined)
}
