import { useState } from 'react'
import { cn } from '@/lib/cn'
import { EmailInboxTab } from './EmailInboxTab'
import { MailboxesTab } from './MailboxesTab'

const TABS = [
  { key: 'inbox', label: 'Inbox' },
  { key: 'mailboxes', label: 'Mailboxes & failures' },
] as const

export function EmailPage() {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]['key']>('inbox')

  return (
    <div className="-m-6">
      <div className="flex border-b border-border px-6">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'border-b-2 px-3 py-2.5 text-small font-medium text-text-secondary hover:text-text-primary',
              activeTab === tab.key ? 'border-brand text-brand' : 'border-transparent',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className={activeTab === 'inbox' ? '' : 'p-6'}>
        {activeTab === 'inbox' ? <EmailInboxTab /> : <MailboxesTab />}
      </div>
    </div>
  )
}
