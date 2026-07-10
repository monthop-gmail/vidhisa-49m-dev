import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { components } from '../api/schema'
import {
  Button,
  Card,
  CardBody,
  ErrorMessage,
  Field,
  Input,
  LoadingState,
  PageHeading,
  Select,
} from '../components/ui'

type ParticipantCreate = components['schemas']['ParticipantCreate']

export const Route = createFileRoute('/participants/$participantId')({
  component: ParticipantEditPage,
})

function emptyForm(): ParticipantCreate {
  return {
    branch_id: '',
    first_name: '',
    last_name: '',
    privacy_accepted: false,
  } as ParticipantCreate
}

function ParticipantEditPage() {
  const { participantId } = Route.useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const idNum = Number(participantId)

  const { data, isLoading, error } = useQuery({
    queryKey: ['participant', idNum],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/participants/{participant_id}', {
        params: { path: { participant_id: idNum } },
      })
      if (error) throw error
      return data
    },
  })

  const [form, setForm] = useState<ParticipantCreate>(emptyForm)
  const [savedAt, setSavedAt] = useState<string | null>(null)

  useEffect(() => {
    if (!data) return
    const d = data as Record<string, unknown>
    setForm({
      branch_id: String(d.branch_id ?? ''),
      member_code: (d.member_code as string | null) ?? null,
      prefix: (d.prefix as string | null) ?? null,
      first_name: String(d.first_name ?? ''),
      last_name: String(d.last_name ?? ''),
      gender: (d.gender as string | null) ?? null,
      age: (d.age as number | null) ?? null,
      sub_district: (d.sub_district as string | null) ?? null,
      district: (d.district as string | null) ?? null,
      province: (d.province as string | null) ?? null,
      phone: (d.phone as string | null) ?? null,
      line_id: (d.line_id as string | null) ?? null,
      enrolled_date: (d.enrolled_date as string | null) ?? null,
      privacy_accepted: Boolean(d.privacy_accepted ?? false),
    } as ParticipantCreate)
  }, [data])

  const saveMut = useMutation({
    mutationFn: async (body: ParticipantCreate) => {
      const { data, error } = await api.PUT('/api/participants/{participant_id}', {
        params: { path: { participant_id: idNum } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      setSavedAt(new Date().toLocaleTimeString())
      qc.invalidateQueries({ queryKey: ['participant', idNum] })
      qc.invalidateQueries({ queryKey: ['participants'] })
    },
  })

  const approveMut = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.PATCH('/api/participants/{participant_id}/approve', {
        params: { path: { participant_id: idNum } },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['participant', idNum] })
      qc.invalidateQueries({ queryKey: ['participants'] })
    },
  })

  const rejectMut = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.PATCH('/api/participants/{participant_id}/reject', {
        params: { path: { participant_id: idNum } },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['participant', idNum] })
      qc.invalidateQueries({ queryKey: ['participants'] })
    },
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  const set = <K extends keyof ParticipantCreate>(k: K, v: ParticipantCreate[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  const currentStatus = String((data as Record<string, unknown> | undefined)?.status ?? 'pending')
  const statusTone =
    currentStatus === 'approved'
      ? 'bg-green-100 text-green-800 border-green-300'
      : currentStatus === 'rejected'
        ? 'bg-red-100 text-red-800 border-red-300'
        : 'bg-amber-100 text-amber-800 border-amber-300'

  return (
    <div className="grid gap-4 max-w-3xl">
      <PageHeading title="Edit Participant" subtitle={`#${participantId}`} />

      <Card>
        <CardBody className="flex flex-wrap items-center gap-3">
          <div className="text-sm text-slate-500">สถานะปัจจุบัน:</div>
          <span className={`inline-flex items-center px-2 py-1 rounded-md border text-sm font-medium ${statusTone}`}>
            {currentStatus}
          </span>
          <div className="ml-auto flex gap-2">
            {currentStatus !== 'approved' && (
              <Button
                variant="success"
                onClick={() => {
                  if (confirm(`อนุมัติผู้เข้าร่วม #${idNum}?`)) approveMut.mutate()
                }}
                disabled={approveMut.isPending}
              >
                {approveMut.isPending ? 'กำลัง approve…' : '✓ Approve'}
              </Button>
            )}
            {currentStatus !== 'rejected' && (
              <Button
                variant="danger"
                onClick={() => {
                  if (confirm(`ปฏิเสธผู้เข้าร่วม #${idNum}?\n(records ยังอยู่ แต่ผู้เข้าร่วมจะไม่แสดงในรายการ approved)`))
                    rejectMut.mutate()
                }}
                disabled={rejectMut.isPending}
              >
                {rejectMut.isPending ? 'กำลัง reject…' : '✗ Reject'}
              </Button>
            )}
          </div>
          {(approveMut.error || rejectMut.error) && (
            <div className="w-full">
              <ErrorMessage>{String(approveMut.error ?? rejectMut.error)}</ErrorMessage>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardBody>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              saveMut.mutate(form)
            }}
            className="grid gap-3"
          >
            <Field label="Branch ID *">
              <Input value={form.branch_id ?? ''} onChange={(e) => set('branch_id', e.target.value)} required />
            </Field>
            <Field label="Member code (รหัสสมาชิกในสาขา)">
              <Input
                value={(form as ParticipantCreate & { member_code?: string | null }).member_code ?? ''}
                onChange={(e) => set('member_code' as keyof ParticipantCreate, (e.target.value || null) as never)}
                placeholder="เช่น 001, WP123"
              />
            </Field>
            <Field label="คำนำหน้า">
              <Input value={form.prefix ?? ''} onChange={(e) => set('prefix', e.target.value || null)} />
            </Field>
            <Field label="ชื่อ *">
              <Input value={form.first_name ?? ''} onChange={(e) => set('first_name', e.target.value)} required />
            </Field>
            <Field label="นามสกุล *">
              <Input value={form.last_name ?? ''} onChange={(e) => set('last_name', e.target.value)} required />
            </Field>
            <Field label="เพศ">
              <Select
                value={form.gender ?? ''}
                onChange={(e) => set('gender', (e.target.value || null) as ParticipantCreate['gender'])}
              >
                <option value="">— ไม่ระบุ —</option>
                <option value="male">ชาย</option>
                <option value="female">หญิง</option>
                <option value="unspecified">ไม่ระบุ</option>
              </Select>
            </Field>
            <Field label="อายุ">
              <Input
                type="number"
                value={form.age ?? ''}
                onChange={(e) => set('age', e.target.value === '' ? null : Number(e.target.value))}
              />
            </Field>
            <Field label="ตำบล/แขวง">
              <Input value={form.sub_district ?? ''} onChange={(e) => set('sub_district', e.target.value || null)} />
            </Field>
            <Field label="อำเภอ/เขต">
              <Input value={form.district ?? ''} onChange={(e) => set('district', e.target.value || null)} />
            </Field>
            <Field label="จังหวัด">
              <Input value={form.province ?? ''} onChange={(e) => set('province', e.target.value || null)} />
            </Field>
            <Field label="เบอร์โทร">
              <Input value={form.phone ?? ''} onChange={(e) => set('phone', e.target.value || null)} />
            </Field>
            <Field label="Line ID">
              <Input value={form.line_id ?? ''} onChange={(e) => set('line_id', e.target.value || null)} />
            </Field>
            <Field label="วันลงทะเบียน">
              <Input
                type="date"
                value={form.enrolled_date ?? ''}
                onChange={(e) => set('enrolled_date', e.target.value || null)}
              />
            </Field>
            <Field label="ยอมรับ Privacy">
              <input
                type="checkbox"
                checked={form.privacy_accepted ?? false}
                onChange={(e) => set('privacy_accepted', e.target.checked)}
                className="h-4 w-4 text-blue-600 rounded border-slate-300 focus:ring-2 focus:ring-blue-500"
              />
            </Field>

            <div className="flex flex-wrap items-center gap-3 mt-3 pt-3 border-t border-slate-100">
              <Button type="submit" disabled={saveMut.isPending}>
                {saveMut.isPending ? 'Saving…' : 'Save'}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate({ to: '/participants' })}>
                Back
              </Button>
              {savedAt && <span className="text-sm text-green-700">บันทึกแล้ว {savedAt}</span>}
              {saveMut.error && <ErrorMessage>{String(saveMut.error)}</ErrorMessage>}
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
