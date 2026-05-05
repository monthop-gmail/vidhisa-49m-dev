import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
import type { components } from '../api/schema'
import { Button, Card, CardBody, ErrorMessage, Field, Input, PageHeading, Select } from '../components/ui'

type RecordCreate = components['schemas']['RecordCreate']

export const Route = createFileRoute('/records/new')({
  component: RecordNewPage,
})

type Mode = 'individual' | 'bulk'

function todayISO(): string {
  return new Date().toISOString().slice(0, 10)
}

function RecordNewPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [mode, setMode] = useState<Mode>('individual')
  const branchId = user?.branch_id ?? ''
  const isCentral = user?.role === 'central_admin'

  return (
    <div className="grid gap-4 max-w-3xl">
      <PageHeading
        title="New Record"
        subtitle={`บันทึกการปฏิบัติ${branchId ? ` · สาขา ${branchId}` : ''}`}
      />

      <div className="flex gap-1 border-b border-slate-200">
        {(['individual', 'bulk'] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition ${
              mode === m
                ? 'border-blue-600 text-blue-700'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            {m === 'individual' ? 'รายบุคคล' : 'แบบกลุ่ม (องค์กร)'}
          </button>
        ))}
      </div>

      {mode === 'individual' ? (
        <IndividualForm
          branchId={branchId}
          isCentral={isCentral}
          onDone={() => {
            qc.invalidateQueries({ queryKey: ['records'] })
            navigate({ to: '/records' })
          }}
        />
      ) : (
        <BulkForm
          branchId={branchId}
          isCentral={isCentral}
          onDone={() => {
            qc.invalidateQueries({ queryKey: ['records'] })
            navigate({ to: '/records' })
          }}
        />
      )}
    </div>
  )
}

// ─── Individual ───────────────────────────────────────────────────

function IndividualForm({
  branchId,
  isCentral,
  onDone,
}: {
  branchId: string
  isCentral: boolean
  onDone: () => void
}) {
  const [thisBranchId, setThisBranchId] = useState(branchId)
  const [participantId, setParticipantId] = useState<number | ''>('')
  const [date, setDate] = useState(todayISO())
  const [morning, setMorning] = useState(true)
  const [afternoon, setAfternoon] = useState(false)
  const [evening, setEvening] = useState(false)
  const [submittedBy, setSubmittedBy] = useState('')

  // load participants of this branch (approved only)
  const partsQ = useQuery({
    queryKey: ['participants-for-record', thisBranchId],
    queryFn: async () => {
      if (!thisBranchId) return []
      const { data, error } = await api.GET('/api/participants', {
        params: { query: { branch_id: thisBranchId, limit: 1000 } },
      })
      if (error) throw error
      return ((data ?? []) as Array<Record<string, unknown>>).filter((p) => p.status === 'approved')
    },
    enabled: Boolean(thisBranchId),
  })
  const parts = partsQ.data ?? []
  const selectedPart = parts.find((p) => Number(p.id) === Number(participantId))

  const slots = (morning ? 1 : 0) + (afternoon ? 1 : 0) + (evening ? 1 : 0)
  const minutes = slots * 5

  // API enforces session ≤ 5 min — submit one POST per checked slot.
  const createMut = useMutation({
    mutationFn: async () => {
      if (!selectedPart) throw new Error('เลือกผู้เข้าร่วม')
      if (slots === 0) throw new Error('เลือกอย่างน้อย 1 รอบ')
      const gender = String(selectedPart.gender ?? 'unspecified')
      const name = `${selectedPart.prefix ?? ''} ${selectedPart.first_name ?? ''} ${selectedPart.last_name ?? ''}`.trim()

      const slotBodies: RecordCreate[] = []
      const buildSlot = (which: 'morning' | 'afternoon' | 'evening'): RecordCreate => {
        const gm = which === 'morning' && gender === 'male' ? 1 : 0
        const gf = which === 'morning' && gender === 'female' ? 1 : 0
        const gu = which === 'morning' && gender !== 'male' && gender !== 'female' ? 1 : 0
        const am = which === 'afternoon' && gender === 'male' ? 1 : 0
        const af = which === 'afternoon' && gender === 'female' ? 1 : 0
        const au = which === 'afternoon' && gender !== 'male' && gender !== 'female' ? 1 : 0
        const em = which === 'evening' && gender === 'male' ? 1 : 0
        const ef = which === 'evening' && gender === 'female' ? 1 : 0
        const eu = which === 'evening' && gender !== 'male' && gender !== 'female' ? 1 : 0
        return {
          type: 'individual',
          branch_id: thisBranchId,
          participant_id: Number(participantId),
          name,
          minutes: 5,
          morning_male: gm,
          morning_female: gf,
          morning_unspecified: gu,
          afternoon_male: am,
          afternoon_female: af,
          afternoon_unspecified: au,
          evening_male: em,
          evening_female: ef,
          evening_unspecified: eu,
          date,
          submitted_by: submittedBy || null,
        }
      }
      if (morning) slotBodies.push(buildSlot('morning'))
      if (afternoon) slotBodies.push(buildSlot('afternoon'))
      if (evening) slotBodies.push(buildSlot('evening'))

      const results = []
      for (const body of slotBodies) {
        const { data, error } = await api.POST('/api/records', { body })
        if (error) throw error
        results.push(data)
      }
      return results
    },
    onSuccess: onDone,
  })

  return (
    <Card>
      <CardBody>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            createMut.mutate()
          }}
          className="grid gap-3"
        >
          <Field label="Branch ID *">
            <Input
              value={thisBranchId}
              onChange={(e) => setThisBranchId(e.target.value)}
              required
              disabled={!isCentral}
            />
          </Field>
          <Field label="ผู้เข้าร่วม *">
            <Select
              value={participantId === '' ? '' : String(participantId)}
              onChange={(e) => setParticipantId(e.target.value === '' ? '' : Number(e.target.value))}
              required
            >
              <option value="">{partsQ.isLoading ? 'กำลังโหลด…' : `— เลือก (${parts.length} คน) —`}</option>
              {parts.map((p) => (
                <option key={String(p.id)} value={String(p.id)}>
                  #{String(p.id)} {String(p.prefix ?? '')} {String(p.first_name ?? '')} {String(p.last_name ?? '')}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="วันที่ *">
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </Field>
          <Field label="รอบที่ปฏิบัติ *">
            <div className="flex gap-4 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={morning}
                  onChange={(e) => setMorning(e.target.checked)}
                  className="h-4 w-4 rounded text-blue-600"
                />
                เช้า 5 นาที
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={afternoon}
                  onChange={(e) => setAfternoon(e.target.checked)}
                  className="h-4 w-4 rounded text-blue-600"
                />
                กลางวัน 5 นาที
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={evening}
                  onChange={(e) => setEvening(e.target.checked)}
                  className="h-4 w-4 rounded text-blue-600"
                />
                เย็น 5 นาที
              </label>
            </div>
          </Field>
          <Field label="รวม">
            <span className="text-lg font-semibold tabular-nums">{minutes} นาที</span>
          </Field>
          <Field label="ผู้บันทึก">
            <Input value={submittedBy} onChange={(e) => setSubmittedBy(e.target.value)} />
          </Field>

          <FormActions pending={createMut.isPending} error={createMut.error} />
        </form>
      </CardBody>
    </Card>
  )
}

// ─── Bulk ─────────────────────────────────────────────────────────

function BulkForm({
  branchId,
  isCentral,
  onDone,
}: {
  branchId: string
  isCentral: boolean
  onDone: () => void
}) {
  const [thisBranchId, setThisBranchId] = useState(branchId)
  const [orgId, setOrgId] = useState('')
  const [date, setDate] = useState(todayISO())
  const [participantCount, setParticipantCount] = useState<number | ''>('')
  const [minutesPerPerson, setMinutesPerPerson] = useState(5)
  const [submittedBy, setSubmittedBy] = useState('')
  const [submittedPhone, setSubmittedPhone] = useState('')

  const orgsQ = useQuery({
    queryKey: ['orgs-for-record', thisBranchId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/organizations')
      if (error) throw error
      const all = (data ?? []) as Array<Record<string, unknown>>
      return all.filter(
        (o) => o.status === 'approved' && (!thisBranchId || o.branch_id === thisBranchId),
      )
    },
  })
  const orgs = orgsQ.data ?? []
  const selectedOrg = orgs.find((o) => o.id === orgId)
  const totalMinutes = (typeof participantCount === 'number' ? participantCount : 0) * minutesPerPerson

  const createMut = useMutation({
    mutationFn: async () => {
      if (!selectedOrg) throw new Error('เลือกองค์กร')
      if (typeof participantCount !== 'number' || participantCount < 1) throw new Error('จำนวนผู้ปฏิบัติต้อง > 0')
      const body: RecordCreate = {
        type: 'bulk',
        branch_id: thisBranchId,
        org_id: orgId,
        name: String(selectedOrg.name ?? ''),
        participant_count: participantCount,
        minutes_per_person: minutesPerPerson,
        minutes: totalMinutes,
        morning_male: 0,
        morning_female: 0,
        morning_unspecified: 0,
        afternoon_male: 0,
        afternoon_female: 0,
        afternoon_unspecified: 0,
        evening_male: 0,
        evening_female: 0,
        evening_unspecified: 0,
        date,
        submitted_by: submittedBy || null,
        submitted_phone: submittedPhone || null,
      }
      const { data, error } = await api.POST('/api/records', { body })
      if (error) throw error
      return data
    },
    onSuccess: onDone,
  })

  return (
    <Card>
      <CardBody>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            createMut.mutate()
          }}
          className="grid gap-3"
        >
          <Field label="Branch ID *">
            <Input
              value={thisBranchId}
              onChange={(e) => setThisBranchId(e.target.value)}
              required
              disabled={!isCentral}
            />
          </Field>
          <Field label="หน่วยงาน *">
            <Select value={orgId} onChange={(e) => setOrgId(e.target.value)} required>
              <option value="">{orgsQ.isLoading ? 'กำลังโหลด…' : `— เลือก (${orgs.length} องค์กร) —`}</option>
              {orgs.map((o) => (
                <option key={String(o.id)} value={String(o.id)}>
                  {String(o.id)} — {String(o.name)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="วันที่ *">
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          </Field>
          <Field label="จำนวนผู้ปฏิบัติ *">
            <Input
              type="number"
              min={1}
              value={participantCount}
              onChange={(e) => setParticipantCount(e.target.value === '' ? '' : Number(e.target.value))}
              required
            />
          </Field>
          <Field label="นาที/คน">
            <Select
              value={minutesPerPerson}
              onChange={(e) => setMinutesPerPerson(Number(e.target.value))}
            >
              <option value={5}>5 นาที (1 รอบ)</option>
              <option value={10}>10 นาที (2 รอบ)</option>
              <option value={15}>15 นาที (3 รอบ)</option>
            </Select>
          </Field>
          <Field label="รวม">
            <span className="text-lg font-semibold tabular-nums">
              {totalMinutes.toLocaleString()} นาที
            </span>
          </Field>
          <Field label="ผู้บันทึก">
            <Input value={submittedBy} onChange={(e) => setSubmittedBy(e.target.value)} />
          </Field>
          <Field label="เบอร์ติดต่อ">
            <Input value={submittedPhone} onChange={(e) => setSubmittedPhone(e.target.value)} />
          </Field>

          <FormActions pending={createMut.isPending} error={createMut.error} />
        </form>
      </CardBody>
    </Card>
  )
}

function FormActions({ pending, error }: { pending: boolean; error: unknown }) {
  const navigate = useNavigate()
  return (
    <div className="flex flex-wrap items-center gap-3 mt-3 pt-3 border-t border-slate-100">
      <Button type="submit" disabled={pending}>
        {pending ? 'Saving…' : 'Save'}
      </Button>
      <Button type="button" variant="secondary" onClick={() => navigate({ to: '/records' })}>
        Cancel
      </Button>
      {error ? <ErrorMessage>{String(error)}</ErrorMessage> : null}
    </div>
  )
}
