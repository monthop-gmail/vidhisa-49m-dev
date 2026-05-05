import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
import type { components } from '../api/schema'
import { Button, Card, CardBody, ErrorMessage, Field, Input, PageHeading, Select } from '../components/ui'

type ParticipantCreate = components['schemas']['ParticipantCreate']

export const Route = createFileRoute('/participants/new')({
  component: ParticipantNewPage,
})

function emptyForm(branchId: string): ParticipantCreate {
  return {
    branch_id: branchId,
    first_name: '',
    last_name: '',
    privacy_accepted: false,
  } as ParticipantCreate
}

function ParticipantNewPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [form, setForm] = useState<ParticipantCreate>(() => emptyForm(user?.branch_id ?? ''))

  const createMut = useMutation({
    mutationFn: async (body: ParticipantCreate) => {
      const { data, error } = await api.POST('/api/participants', { body })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['participants'] })
      navigate({ to: '/participants' })
    },
  })

  const set = <K extends keyof ParticipantCreate>(k: K, v: ParticipantCreate[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  return (
    <div className="grid gap-4 max-w-3xl">
      <PageHeading title="New Participant" subtitle="ลงทะเบียนผู้เข้าร่วมรายบุคคล" />

      <Card>
        <CardBody>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              createMut.mutate(form)
            }}
            className="grid gap-3"
          >
            <Field label="Branch ID *">
              <Input
                value={form.branch_id}
                onChange={(e) => set('branch_id', e.target.value)}
                required
                disabled={user?.role !== 'central_admin' && Boolean(user?.branch_id)}
              />
            </Field>
            <Field label="คำนำหน้า">
              <Select
                value={form.prefix ?? ''}
                onChange={(e) => set('prefix', (e.target.value || null) as ParticipantCreate['prefix'])}
              >
                <option value="">— เลือก —</option>
                <option value="นาย">นาย</option>
                <option value="นาง">นาง</option>
                <option value="นางสาว">นางสาว</option>
                <option value="ด.ช.">ด.ช.</option>
                <option value="ด.ญ.">ด.ญ.</option>
              </Select>
            </Field>
            <Field label="ชื่อ *">
              <Input value={form.first_name} onChange={(e) => set('first_name', e.target.value)} required />
            </Field>
            <Field label="นามสกุล *">
              <Input value={form.last_name} onChange={(e) => set('last_name', e.target.value)} required />
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
              <Button type="submit" disabled={createMut.isPending}>
                {createMut.isPending ? 'Creating…' : 'Create'}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate({ to: '/participants' })}>
                Cancel
              </Button>
              {createMut.error && <ErrorMessage>{String(createMut.error)}</ErrorMessage>}
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
