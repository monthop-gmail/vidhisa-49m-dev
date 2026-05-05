import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useSortable } from '../lib/sort'
import {
  Card,
  CardBody,
  EmptyState,
  ErrorMessage,
  Input,
  LoadingState,
  PageHeading,
  SortableTh,
  Table,
  Td,
  Th,
  Thead,
  Tr,
} from '../components/ui'

export const Route = createFileRoute('/branches/')({
  component: BranchesPage,
})

type SortKey = 'id' | 'name' | 'group_id' | 'province' | 'minutes' | 'hasGeo'

function BranchesPage() {
  const [q, setQ] = useState('')
  const { sort, toggleSort, sortRows } = useSortable<Record<string, unknown>, SortKey>({
    defaultSort: { key: 'id', dir: 'asc' },
    getValue: (r, k) => {
      if (k === 'minutes') return Number(r.minutes ?? r.total_minutes ?? 0)
      if (k === 'hasGeo') return r.latitude != null && r.longitude != null ? 1 : 0
      return r[k]
    },
  })

  const { data, isLoading, error } = useQuery({
    queryKey: ['branches'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/branches')
      if (error) throw error
      return data
    },
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  const rows = (Array.isArray(data) ? data : []) as Array<Record<string, unknown>>
  const filtered = q
    ? rows.filter((r) => `${r.id ?? ''} ${r.name ?? ''} ${r.province ?? ''}`.toLowerCase().includes(q.toLowerCase()))
    : rows
  const sorted = sortRows(filtered)

  return (
    <div className="grid gap-4">
      <PageHeading
        title="Branches"
        subtitle={`${rows.length.toLocaleString()} สาขาทั้งหมด`}
        right={<Input placeholder="ค้นหา id / ชื่อ / จังหวัด" value={q} onChange={(e) => setQ(e.target.value)} className="!w-72" />}
      />

      <Card>
        <CardBody className="p-0">
          {filtered.length === 0 ? (
            <div className="p-8">
              <EmptyState>ไม่พบสาขา</EmptyState>
            </div>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <SortableTh sortKey="id" sort={sort} onSort={toggleSort}>ID</SortableTh>
                  <SortableTh sortKey="name" sort={sort} onSort={toggleSort}>ชื่อ</SortableTh>
                  <SortableTh sortKey="group_id" sort={sort} onSort={toggleSort}>กลุ่ม</SortableTh>
                  <SortableTh sortKey="province" sort={sort} onSort={toggleSort}>จังหวัด</SortableTh>
                  <SortableTh sortKey="hasGeo" sort={sort} onSort={toggleSort} align="center">Lat/Lng</SortableTh>
                  <SortableTh sortKey="minutes" sort={sort} onSort={toggleSort} align="right">นาที</SortableTh>
                  <Th></Th>
                </Tr>
              </Thead>
              <tbody>
                {sorted.slice(0, 400).map((b) => {
                  const r = b as Record<string, unknown>
                  const id = String(r.id ?? r.branch_id ?? '')
                  const hasGeo = r.latitude != null && r.longitude != null
                  return (
                    <Tr key={id}>
                      <Td>
                        <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{id}</code>
                      </Td>
                      <Td>{String(r.name ?? r.branch_name ?? '')}</Td>
                      <Td className="text-slate-500 text-xs">{String(r.group_id ?? '—')}</Td>
                      <Td className="text-slate-600">{String(r.province ?? '')}</Td>
                      <Td align="center">
                        {hasGeo ? <span className="text-green-600 text-xs">✓</span> : <span className="text-amber-600 text-xs">—</span>}
                      </Td>
                      <Td align="right">{Number(r.minutes ?? r.total_minutes ?? 0).toLocaleString()}</Td>
                      <Td>
                        <Link
                          to="/branches/$branchId"
                          params={{ branchId: id }}
                          className="text-blue-600 hover:underline text-sm"
                        >
                          Edit →
                        </Link>
                      </Td>
                    </Tr>
                  )
                })}
              </tbody>
            </Table>
          )}
        </CardBody>
      </Card>
      {filtered.length > 400 && (
        <div className="text-xs text-slate-500">แสดง 400 รายการแรกจาก {filtered.length}</div>
      )}
    </div>
  )
}
