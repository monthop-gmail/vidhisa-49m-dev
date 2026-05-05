import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
import { useSortable } from '../lib/sort'
import { OrgDetailModal } from '../components/DetailDrawer'
import {
  Button,
  Card,
  CardBody,
  EmptyState,
  ErrorMessage,
  Input,
  LoadingState,
  PageHeading,
  SortableTh,
  StatusBadge,
  Table,
  Td,
  Th,
  Thead,
  Tr,
} from '../components/ui'

export const Route = createFileRoute('/organizations/')({
  component: OrganizationsListPage,
})

type SortKey = 'id' | 'name' | 'org_type' | 'branch_id' | 'province' | 'status' | 'total_minutes'

function OrganizationsListPage() {
  const { user } = useAuth()
  const isCentral = user?.role === 'central_admin'
  const [q, setQ] = useState('')
  const [detailOrgId, setDetailOrgId] = useState<string | null>(null)
  const { sort, toggleSort, sortRows } = useSortable<Record<string, unknown>, SortKey>({
    defaultSort: { key: 'id', dir: 'asc' },
    getValue: (r, k) => (k === 'total_minutes' ? Number(r.total_minutes ?? 0) : r[k]),
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['organizations'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/organizations')
      if (error) throw error
      return data
    },
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  const allRows = (Array.isArray(data) ? data : []) as Array<Record<string, unknown>>
  const rows = isCentral
    ? allRows
    : allRows.filter((r) => String(r.branch_id ?? '') === String(user?.branch_id ?? ''))
  const filtered = q
    ? rows.filter((r) =>
        `${r.id ?? ''} ${r.name ?? ''} ${r.province ?? ''} ${r.branch_id ?? ''}`.toLowerCase().includes(q.toLowerCase()),
      )
    : rows
  const sorted = sortRows(filtered)

  return (
    <div className="grid gap-4">
      <PageHeading
        title="Organizations"
        subtitle={`${rows.length.toLocaleString()} องค์กร${isCentral ? '' : ` ของ ${user?.branch_id}`}`}
        right={
          <div className="flex items-center gap-2">
            <Input placeholder="ค้นหา id / ชื่อ / จังหวัด" value={q} onChange={(e) => setQ(e.target.value)} className="!w-72" />
            <Link to="/organizations/new">
              <Button>+ New</Button>
            </Link>
          </div>
        }
      />

      <Card>
        <CardBody className="p-0">
          {filtered.length === 0 ? (
            <div className="p-8">
              <EmptyState>ไม่พบองค์กร</EmptyState>
            </div>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <SortableTh sortKey="id" sort={sort} onSort={toggleSort}>ID</SortableTh>
                  <SortableTh sortKey="name" sort={sort} onSort={toggleSort}>ชื่อ</SortableTh>
                  <SortableTh sortKey="org_type" sort={sort} onSort={toggleSort}>ประเภท</SortableTh>
                  <SortableTh sortKey="branch_id" sort={sort} onSort={toggleSort}>สาขา</SortableTh>
                  <SortableTh sortKey="province" sort={sort} onSort={toggleSort}>จังหวัด</SortableTh>
                  <SortableTh sortKey="status" sort={sort} onSort={toggleSort}>Status</SortableTh>
                  <SortableTh sortKey="total_minutes" sort={sort} onSort={toggleSort} align="right">นาที</SortableTh>
                  <Th></Th>
                </Tr>
              </Thead>
              <tbody>
                {sorted.slice(0, 200).map((r) => (
                  <Tr key={String(r.id)}>
                    <Td>
                      <button onClick={() => setDetailOrgId(String(r.id))} className="text-blue-600 hover:underline">
                        <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{String(r.id ?? '')}</code>
                      </button>
                    </Td>
                    <Td>
                      <button onClick={() => setDetailOrgId(String(r.id))} className="text-left hover:underline">
                        {String(r.name ?? '')}
                      </button>
                    </Td>
                    <Td className="text-slate-600">{String(r.org_type ?? '')}</Td>
                    <Td className="text-slate-600">{String(r.branch_id ?? '')}</Td>
                    <Td className="text-slate-600">{String(r.province ?? '')}</Td>
                    <Td>{r.status ? <StatusBadge status={String(r.status)} /> : null}</Td>
                    <Td align="right">{Number(r.total_minutes ?? 0).toLocaleString()}</Td>
                    <Td>
                      <Link
                        to="/organizations/$orgId"
                        params={{ orgId: String(r.id) }}
                        className="text-blue-600 hover:underline text-sm"
                      >
                        Edit →
                      </Link>
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

      <OrgDetailModal orgId={detailOrgId} onClose={() => setDetailOrgId(null)} />
    </div>
  )
}
