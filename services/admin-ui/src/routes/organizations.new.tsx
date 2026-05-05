import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../lib/auth'
import type { components } from '../api/schema'
import { Button, Card, CardBody, ErrorMessage, Field, Input, PageHeading } from '../components/ui'

type OrganizationCreate = components['schemas']['OrganizationCreate']

export const Route = createFileRoute('/organizations/new')({
  component: OrganizationNewPage,
})

function emptyForm(branchId: string): OrganizationCreate {
  return {
    id: '',
    name: '',
    branch_id: branchId || null,
    gender_male: 0,
    gender_female: 0,
    gender_unspecified: 0,
  } as OrganizationCreate
}

function OrganizationNewPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [form, setForm] = useState<OrganizationCreate>(() => emptyForm(user?.branch_id ?? ''))

  const createMut = useMutation({
    mutationFn: async (body: OrganizationCreate) => {
      const { data, error } = await api.POST('/api/organizations', { body })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['organizations'] })
      navigate({ to: '/organizations' })
    },
  })

  const set = <K extends keyof OrganizationCreate>(k: K, v: OrganizationCreate[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  return (
    <div className="grid gap-4 max-w-3xl">
      <PageHeading title="New Organization" subtitle="สร้างองค์กรใหม่" />

      <Card>
        <CardBody>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              createMut.mutate(form)
            }}
            className="grid gap-3"
          >
            <Field label="ID *">
              <Input value={form.id} onChange={(e) => set('id', e.target.value)} required placeholder="เช่น B001-02" />
            </Field>
            <Field label="ชื่อองค์กร *">
              <Input value={form.name} onChange={(e) => set('name', e.target.value)} required />
            </Field>
            <Field label="ประเภท">
              <Input value={form.org_type ?? ''} onChange={(e) => set('org_type', e.target.value || null)} placeholder="โรงเรียน / วัด / บริษัท" />
            </Field>
            <Field label="Branch ID *">
              <Input value={form.branch_id ?? ''} onChange={(e) => set('branch_id', e.target.value || null)} required disabled={user?.role !== 'central_admin' && Boolean(user?.branch_id)} />
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
            <Field label="อีเมล">
              <Input type="email" value={form.email ?? ''} onChange={(e) => set('email', e.target.value || null)} />
            </Field>
            <Field label="ผู้เข้าร่วมสูงสุด">
              <Input
                type="number"
                value={form.max_participants ?? ''}
                onChange={(e) => set('max_participants', e.target.value === '' ? null : Number(e.target.value))}
              />
            </Field>
            <Field label="ชาย">
              <Input type="number" value={form.gender_male} onChange={(e) => set('gender_male', Number(e.target.value || 0))} />
            </Field>
            <Field label="หญิง">
              <Input type="number" value={form.gender_female} onChange={(e) => set('gender_female', Number(e.target.value || 0))} />
            </Field>
            <Field label="ไม่ระบุ">
              <Input
                type="number"
                value={form.gender_unspecified}
                onChange={(e) => set('gender_unspecified', Number(e.target.value || 0))}
              />
            </Field>
            <Field label="ผู้ติดต่อ">
              <Input value={form.contact_name ?? ''} onChange={(e) => set('contact_name', e.target.value || null)} />
            </Field>
            <Field label="เบอร์โทร">
              <Input value={form.contact_phone ?? ''} onChange={(e) => set('contact_phone', e.target.value || null)} />
            </Field>

            <div className="flex flex-wrap items-center gap-3 mt-3 pt-3 border-t border-slate-100">
              <Button type="submit" disabled={createMut.isPending}>
                {createMut.isPending ? 'Creating…' : 'Create'}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate({ to: '/organizations' })}>
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
