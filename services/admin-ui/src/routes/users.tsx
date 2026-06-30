import { createFileRoute, redirect } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getAuth } from '../lib/auth'
import { Modal } from '../components/Modal'
import { useSortable } from '../lib/sort'
import {
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  ErrorMessage,
  Field,
  Input,
  LoadingState,
  PageHeading,
  Select,
  SortableTh,
  StatusBadge,
  Table,
  Td,
  Th,
  Thead,
  Tr,
} from '../components/ui'

type UserSortKey = 'id' | 'username' | 'full_name' | 'email' | 'role' | 'branch_id' | 'status'

export const Route = createFileRoute('/users')({
  beforeLoad: () => {
    const { user } = getAuth()
    if (user && user.role !== 'central_admin') {
      throw redirect({ to: '/' })
    }
  },
  component: UsersPage,
})

type AppUser = {
  id: number
  username: string
  full_name: string
  email: string | null
  phone: string | null
  role: string
  branch_id: string | null
  branch_ids: string[]
  status: string
}

type RoleFilter = '' | 'central_admin' | 'branch_admin'
type StatusFilter = '' | 'active' | 'disabled'

function UsersPage() {
  const [q, setQ] = useState('')
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('')
  const [editing, setEditing] = useState<AppUser | null>(null)
  const { sort, toggleSort, sortRows } = useSortable<AppUser, UserSortKey>({
    defaultSort: { key: 'id', dir: 'asc' },
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/users')
      if (error) throw error
      return (data ?? []) as AppUser[]
    },
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  const all = data ?? []
  const filtered = sortRows(
    all.filter((u) => {
      if (roleFilter && u.role !== roleFilter) return false
      if (statusFilter && u.status !== statusFilter) return false
      if (q) {
        const hay = `${u.id} ${u.username} ${u.full_name} ${u.email ?? ''} ${u.branch_id ?? ''}`.toLowerCase()
        if (!hay.includes(q.toLowerCase())) return false
      }
      return true
    }),
  )

  return (
    <div className="grid gap-4">
      <PageHeading
        title="Users"
        subtitle={`${all.length} users · ${all.filter((u) => u.role === 'branch_admin').length} branch admins · ${all.filter((u) => u.role === 'central_admin').length} central`}
      />

      <Card>
        <CardBody className="flex flex-wrap items-end gap-3">
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">Role</span>
            <Select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value as RoleFilter)} className="!w-44">
              <option value="">— ทุก role —</option>
              <option value="central_admin">central_admin</option>
              <option value="branch_admin">branch_admin</option>
            </Select>
          </label>
          <label className="grid gap-1">
            <span className="text-xs text-slate-500">Status</span>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as StatusFilter)} className="!w-36">
              <option value="">— ทุก status —</option>
              <option value="active">active</option>
              <option value="disabled">disabled</option>
            </Select>
          </label>
          <label className="grid gap-1 ml-auto">
            <span className="text-xs text-slate-500">ค้นหา</span>
            <Input
              placeholder="username / ชื่อ / email / branch_id"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="!w-80"
            />
          </label>
        </CardBody>
      </Card>

      <Card>
        <CardBody className="p-0">
          {filtered.length === 0 ? (
            <div className="p-8">
              <EmptyState>ไม่พบ user</EmptyState>
            </div>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <SortableTh sortKey="id" sort={sort} onSort={toggleSort}>ID</SortableTh>
                  <SortableTh sortKey="username" sort={sort} onSort={toggleSort}>Username</SortableTh>
                  <SortableTh sortKey="full_name" sort={sort} onSort={toggleSort}>ชื่อ</SortableTh>
                  <SortableTh sortKey="email" sort={sort} onSort={toggleSort}>Email</SortableTh>
                  <Th>เบอร์</Th>
                  <SortableTh sortKey="role" sort={sort} onSort={toggleSort}>Role</SortableTh>
                  <SortableTh sortKey="branch_id" sort={sort} onSort={toggleSort}>สาขา</SortableTh>
                  <SortableTh sortKey="status" sort={sort} onSort={toggleSort}>Status</SortableTh>
                  <Th align="right">Actions</Th>
                </Tr>
              </Thead>
              <tbody>
                {filtered.slice(0, 200).map((u) => (
                  <Tr key={u.id}>
                    <Td className="text-slate-500">#{u.id}</Td>
                    <Td className="font-mono text-xs">{u.username}</Td>
                    <Td>{u.full_name}</Td>
                    <Td className="text-slate-600 text-xs">{u.email ?? '—'}</Td>
                    <Td className="text-slate-600 text-xs">{u.phone ?? '—'}</Td>
                    <Td>
                      <Badge tone={u.role === 'central_admin' ? 'blue' : 'gray'}>{u.role}</Badge>
                    </Td>
                    <Td>
                      {(u.branch_ids && u.branch_ids.length > 0) ? (
                        <span className="flex flex-wrap gap-1">
                          {u.branch_ids.map((b) => (
                            <code key={b} className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{b}</code>
                          ))}
                        </span>
                      ) : u.branch_id ? (
                        <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{u.branch_id}</code>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </Td>
                    <Td>
                      <StatusBadge status={u.status} />
                    </Td>
                    <Td align="right">
                      <Button size="sm" variant="secondary" onClick={() => setEditing(u)}>
                        Edit
                      </Button>
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          )}
        </CardBody>
      </Card>
      {filtered.length > 200 && (
        <div className="text-xs text-slate-500">แสดง 200 รายการแรกจาก {filtered.length}</div>
      )}

      <EditUserModal user={editing} onClose={() => setEditing(null)} />
    </div>
  )
}

// ─── Edit user modal ──────────────────────────────────────────────

type EditForm = {
  username: string
  full_name: string
  email: string
  phone: string
  branch_id: string
  branch_ids: string  // comma-separated for simple input
  status: string
}

function EditUserModal({ user, onClose }: { user: AppUser | null; onClose: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<EditForm>({
    username: '',
    full_name: '',
    email: '',
    phone: '',
    branch_id: '',
    branch_ids: '',
    status: 'active',
  })
  const [newPassword, setNewPassword] = useState('')
  const [resetMsg, setResetMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    if (!user) return
    setForm({
      username: user.username,
      full_name: user.full_name,
      email: user.email ?? '',
      phone: user.phone ?? '',
      branch_id: user.branch_id ?? '',
      branch_ids: (user.branch_ids ?? []).join(', '),
      status: user.status,
    })
    setNewPassword('')
    setResetMsg(null)
  }, [user])

  const saveMut = useMutation({
    mutationFn: async (body: EditForm) => {
      const branch_ids = body.branch_ids
        .split(/[,\s]+/)
        .map((s) => s.trim())
        .filter(Boolean)
      const payload = { ...body, branch_ids }
      const { data, error } = await api.PATCH('/api/users/{user_id}', {
        params: { path: { user_id: user!.id } },
        body: payload,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      onClose()
    },
  })

  const resetPasswordMut = useMutation({
    mutationFn: async (password: string) => {
      const token = getAuth().token
      const res = await fetch(`/api/users/${user!.id}/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ password }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail?.message ?? `${res.status}`)
      }
      return res.json()
    },
    onSuccess: () => {
      setResetMsg({ ok: true, text: 'เปลี่ยนรหัสผ่านสำเร็จ' })
      setNewPassword('')
    },
    onError: (err: Error) => setResetMsg({ ok: false, text: err.message }),
  })

  const set = <K extends keyof EditForm>(k: K, v: EditForm[K]) => setForm((f) => ({ ...f, [k]: v }))

  return (
    <Modal open={user !== null} onClose={onClose} title={`Edit user · #${user?.id ?? ''}`}>
      {user && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            saveMut.mutate(form)
          }}
          className="grid gap-3"
        >
          <Field label="Username">
            <Input value={form.username} onChange={(e) => set('username', e.target.value)} />
          </Field>
          <Field label="ชื่อเต็ม">
            <Input value={form.full_name} onChange={(e) => set('full_name', e.target.value)} />
          </Field>
          <Field label="Email">
            <Input type="email" value={form.email} onChange={(e) => set('email', e.target.value)} />
          </Field>
          <Field label="เบอร์โทร">
            <Input value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="เช่น 0812345678" />
          </Field>
          <Field label="Branch ID (สาขาหลัก)">
            <Input
              value={form.branch_id}
              onChange={(e) => set('branch_id', e.target.value)}
              placeholder={user.role === 'central_admin' ? '(ไม่ใช่)' : 'เช่น B012'}
              disabled={user.role === 'central_admin'}
            />
          </Field>
          <Field label="Branch IDs (สาขาทั้งหมดที่ดูแล — comma-separated)">
            <Input
              value={form.branch_ids}
              onChange={(e) => set('branch_ids', e.target.value)}
              placeholder={user.role === 'central_admin' ? '(ไม่ใช่)' : 'เช่น B012, B047, B101'}
              disabled={user.role === 'central_admin'}
            />
          </Field>
          <Field label="Status">
            <Select value={form.status} onChange={(e) => set('status', e.target.value)}>
              <option value="active">active</option>
              <option value="disabled">disabled</option>
            </Select>
          </Field>
          <Field label="Role">
            <span className="text-sm text-slate-600">
              <Badge tone={user.role === 'central_admin' ? 'blue' : 'gray'}>{user.role}</Badge>
              <span className="text-xs text-slate-400 ml-2">(แก้ไม่ได้ผ่าน UI นี้)</span>
            </span>
          </Field>

          <div className="flex flex-wrap items-center gap-3 mt-2 pt-3 border-t border-slate-100">
            <Button type="submit" disabled={saveMut.isPending}>
              {saveMut.isPending ? 'Saving…' : 'Save'}
            </Button>
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            {saveMut.error && <ErrorMessage>{String(saveMut.error)}</ErrorMessage>}
          </div>
        </form>
      )}

      {user && (
        <div className="mt-4 pt-4 border-t border-slate-200 grid gap-2">
          <div className="text-sm font-semibold text-slate-700">เปลี่ยนรหัสผ่าน</div>
          <Field label="รหัสผ่านใหม่ (≥ 6 ตัวอักษร)">
            <Input
              type="text"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="พิมพ์รหัสใหม่"
              autoComplete="new-password"
            />
          </Field>
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="secondary"
              disabled={newPassword.length < 6 || resetPasswordMut.isPending}
              onClick={() => resetPasswordMut.mutate(newPassword)}
            >
              {resetPasswordMut.isPending ? 'กำลังเปลี่ยน…' : 'รีเซ็ตรหัสผ่าน'}
            </Button>
            {resetMsg && (
              <span className={`text-sm ${resetMsg.ok ? 'text-emerald-600' : 'text-red-600'}`}>{resetMsg.text}</span>
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}
