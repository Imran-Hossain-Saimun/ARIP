import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ColumnDef } from '@tanstack/react-table'
import { Plus } from 'lucide-react'
import { DataTable, EmptyState, ErrorState, Modal, StatusBadge } from '@/design-system/primitives'
import { ApiError } from '@/lib/api'
import type { RoleName } from '@/lib/rbac'
import { listDepartments } from '@/features/reference/api'
import { createDepartment, createUser, listUsers, updateUser } from './api'
import type { AdminUserOut } from './types'

const ROLES: RoleName[] = ['super_admin', 'admin', 'knowledge_manager', 'dept_manager', 'support_agent', 'executive', 'auditor', 'customer']

function NewUserForm({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<RoleName>('support_agent')
  const [departmentId, setDepartmentId] = useState('')
  const [password, setPassword] = useState('')
  const { data: departments } = useQuery({ queryKey: ['departments'], queryFn: listDepartments })

  const mutation = useMutation({
    mutationFn: () => createUser({ email, full_name: fullName, role, department_id: departmentId || undefined, password }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setEmail('')
      setFullName('')
      setPassword('')
      onClose()
    },
  })

  if (!open) return null

  return (
    <Modal onClose={onClose} title="New user">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <div>
          <label className="mb-1 block text-small text-text-secondary">Email</label>
          <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand" />
        </div>
        <div>
          <label className="mb-1 block text-small text-text-secondary">Full name</label>
          <input required value={fullName} onChange={(e) => setFullName(e.target.value)} className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-small text-text-secondary">Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value as RoleName)} className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand">
              {ROLES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-small text-text-secondary">Department</label>
            <select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand">
              <option value="">—</option>
              {departments?.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="mb-1 block text-small text-text-secondary">Temporary password</label>
          <input required type="text" value={password} onChange={(e) => setPassword(e.target.value)} className="h-8 w-full rounded-control border border-border-strong px-2.5 font-mono text-body outline-none focus:border-brand" />
        </div>
        {mutation.isError && <p className="text-small text-danger">{mutation.error instanceof ApiError ? mutation.error.message : 'Could not create this user.'}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="h-8 rounded-control border border-border-strong px-3 text-small">Cancel</button>
          <button type="submit" disabled={mutation.isPending} className="h-8 rounded-control bg-brand px-3 text-small font-medium text-white hover:bg-brand-hover disabled:opacity-60">
            {mutation.isPending ? 'Creating…' : 'Create user'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

function NewDepartmentForm({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')

  const mutation = useMutation({
    mutationFn: () => createDepartment({ name, slug: name.toLowerCase().replace(/[^a-z0-9]+/g, '-') }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['departments'] })
      setName('')
      onClose()
    },
  })

  if (!open) return null

  return (
    <Modal onClose={onClose} title="New department" width={420}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          mutation.mutate()
        }}
        className="space-y-3"
      >
        <div>
          <label className="mb-1 block text-small text-text-secondary">Name</label>
          <input required value={name} onChange={(e) => setName(e.target.value)} className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand" />
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="h-8 rounded-control border border-border-strong px-3 text-small">Cancel</button>
          <button type="submit" disabled={mutation.isPending} className="h-8 rounded-control bg-brand px-3 text-small font-medium text-white hover:bg-brand-hover disabled:opacity-60">
            Create
          </button>
        </div>
      </form>
    </Modal>
  )
}

export function AdminPage() {
  const queryClient = useQueryClient()
  const [userFormOpen, setUserFormOpen] = useState(false)
  const [deptFormOpen, setDeptFormOpen] = useState(false)

  const { data: users, isLoading, error, refetch } = useQuery({ queryKey: ['admin-users'], queryFn: listUsers })
  const { data: departments } = useQuery({ queryKey: ['departments'], queryFn: listDepartments })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) => updateUser(id, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  const columns: ColumnDef<AdminUserOut, any>[] = [
    { accessorKey: 'full_name', header: 'Name', size: 180 },
    { accessorKey: 'email', header: 'Email', size: 240 },
    { accessorKey: 'role', header: 'Role', size: 140, cell: (info) => <span className="capitalize">{info.getValue<string>().replace('_', ' ')}</span> },
    {
      id: 'status',
      header: 'Status',
      size: 100,
      cell: ({ row }) => <StatusBadge variant={row.original.is_active ? 'success' : 'neutral'} label={row.original.is_active ? 'active' : 'inactive'} />,
    },
    {
      id: 'actions',
      header: '',
      size: 100,
      cell: ({ row }) => (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            toggleActiveMutation.mutate({ id: row.original.id, isActive: !row.original.is_active })
          }}
          className="h-6 rounded-control border border-border-strong px-2 text-small hover:bg-surface-sunken"
        >
          {row.original.is_active ? 'Deactivate' : 'Activate'}
        </button>
      ),
    },
  ]

  if (error) {
    return <ErrorState message={error instanceof ApiError ? error.message : 'Could not load admin data.'} onRetry={() => refetch()} />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-display font-bold text-text-primary">Administration</h1>
      </div>

      <section>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-h1 font-semibold text-text-primary">Users</h2>
          <button type="button" onClick={() => setUserFormOpen(true)} className="flex h-8 items-center gap-1.5 rounded-control bg-brand px-3 text-small font-medium text-white hover:bg-brand-hover">
            <Plus size={14} /> New user
          </button>
        </div>
        <DataTable
          columns={columns}
          data={users ?? []}
          getRowId={(u) => u.id}
          loading={isLoading}
          emptyState={<EmptyState headline="No users" />}
        />
      </section>

      <section>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-h1 font-semibold text-text-primary">Departments</h2>
          <button type="button" onClick={() => setDeptFormOpen(true)} className="flex h-8 items-center gap-1.5 rounded-control border border-border-strong px-3 text-small font-medium hover:bg-surface-sunken">
            <Plus size={14} /> New department
          </button>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {departments?.map((d) => (
            <div key={d.id} className="rounded-control border border-border bg-surface p-3 text-small">
              {d.name}
            </div>
          ))}
        </div>
      </section>

      <NewUserForm open={userFormOpen} onClose={() => setUserFormOpen(false)} />
      <NewDepartmentForm open={deptFormOpen} onClose={() => setDeptFormOpen(false)} />
    </div>
  )
}
