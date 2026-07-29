export type MailboxProvider = 'mailhog' | 'imap' | 'graph'
export type MailboxStatus = 'connected' | 'disconnected' | 'error'

export interface MailboxOut {
  id: string
  name: string
  email_address: string
  provider: MailboxProvider
  department_id: string | null
  status: MailboxStatus
  last_synced_at: string | null
}

export interface SyncResult {
  created: number
  threaded: number
  failed: number
}

export interface ParseFailureOut {
  id: string
  mailbox_id: string
  raw_subject: string | null
  raw_from: string | null
  error_message: string
  resolved: boolean
  created_at: string
}
