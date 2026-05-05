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
    })
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

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  const set = <K extends keyof ParticipantCreate>(k: K, v: ParticipantCreate[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  return (
    <div className="grid gap-4 max-w-3xl">
      <PageHeading title="Edit Participant" subtitle={`#${participantId}`} />

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
