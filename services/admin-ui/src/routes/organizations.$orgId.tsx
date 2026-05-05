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
} from '../components/ui'

type OrganizationCreate = components['schemas']['OrganizationCreate']

export const Route = createFileRoute('/organizations/$orgId')({
  component: OrganizationEditPage,
})

const TEXT_FIELDS: Array<{ key: keyof OrganizationCreate; label: string; type?: string }> = [
  { key: 'id', label: 'ID' },
  { key: 'name', label: 'ชื่อองค์กร' },
  { key: 'org_type', label: 'ประเภท' },
  { key: 'branch_id', label: 'Branch ID' },
  { key: 'sub_district', label: 'ตำบล/แขวง' },
  { key: 'district', label: 'อำเภอ/เขต' },
  { key: 'province', label: 'จังหวัด' },
  { key: 'email', label: 'อีเมล', type: 'email' },
  { key: 'contact_name', label: 'ผู้ติดต่อ' },
  { key: 'contact_phone', label: 'เบอร์โทร' },
  { key: 'contact_line_id', label: 'Line ID' },
  { key: 'contact', label: 'หมายเหตุติดต่อ' },
]

const NUMBER_FIELDS: Array<{ key: keyof OrganizationCreate; label: string }> = [
  { key: 'max_participants', label: 'ผู้เข้าร่วมสูงสุด' },
  { key: 'gender_male', label: 'ชาย' },
  { key: 'gender_female', label: 'หญิง' },
  { key: 'gender_unspecified', label: 'ไม่ระบุ' },
  { key: 'latitude', label: 'Latitude' },
  { key: 'longitude', label: 'Longitude' },
]

const DATE_FIELDS: Array<{ key: keyof OrganizationCreate; label: string }> = [
  { key: 'enrolled_date', label: 'วันลงทะเบียน' },
  { key: 'enrolled_until', label: 'วันสิ้นสุด' },
]

function emptyForm(): OrganizationCreate {
  return {
    id: '',
    name: '',
    gender_male: 0,
    gender_female: 0,
    gender_unspecified: 0,
  } as OrganizationCreate
}

function OrganizationEditPage() {
  const { orgId } = Route.useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['organization', orgId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/organizations/{org_id}', {
        params: { path: { org_id: orgId } },
      })
      if (error) throw error
      return data
    },
  })

  const [form, setForm] = useState<OrganizationCreate>(emptyForm)
  const [savedAt, setSavedAt] = useState<string | null>(null)

  useEffect(() => {
    if (!data) return
    const d = data as Record<string, unknown>
    setForm({
      id: String(d.id ?? orgId),
      name: String(d.name ?? ''),
      org_type: (d.org_type as string | null) ?? null,
      branch_id: (d.branch_id as string | null) ?? null,
      sub_district: (d.sub_district as string | null) ?? null,
      district: (d.district as string | null) ?? null,
      province: (d.province as string | null) ?? null,
      email: (d.email as string | null) ?? null,
      max_participants: (d.max_participants as number | null) ?? null,
      gender_male: Number(d.gender_male ?? 0),
      gender_female: Number(d.gender_female ?? 0),
      gender_unspecified: Number(d.gender_unspecified ?? 0),
      contact_name: (d.contact_name as string | null) ?? null,
      contact_phone: (d.contact_phone as string | null) ?? null,
      contact_line_id: (d.contact_line_id as string | null) ?? null,
      enrolled_date: (d.enrolled_date as string | null) ?? null,
      enrolled_until: (d.enrolled_until as string | null) ?? null,
      latitude: (d.latitude as number | null) ?? null,
      longitude: (d.longitude as number | null) ?? null,
      contact: (d.contact as string | null) ?? null,
    })
  }, [data, orgId])

  const saveMut = useMutation({
    mutationFn: async (body: OrganizationCreate) => {
      const { data, error } = await api.PUT('/api/organizations/{org_id}', {
        params: { path: { org_id: orgId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      setSavedAt(new Date().toLocaleTimeString())
      qc.invalidateQueries({ queryKey: ['organization', orgId] })
      qc.invalidateQueries({ queryKey: ['organizations'] })
    },
  })

  const deleteMut = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.DELETE('/api/organizations/{org_id}', {
        params: { path: { org_id: orgId } },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['organizations'] })
      navigate({ to: '/organizations' })
    },
  })

  if (isLoading) return <LoadingState />
  if (error) return <ErrorMessage>{String(error)}</ErrorMessage>

  const setField = <K extends keyof OrganizationCreate>(key: K, value: OrganizationCreate[K]) =>
    setForm((f) => ({ ...f, [key]: value }))

  return (
    <div className="grid gap-4 max-w-3xl">
      <PageHeading
        title="Edit Organization"
        subtitle={
          <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded">{orgId}</code>
        }
      />

      <Card>
        <CardBody>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              saveMut.mutate(form)
            }}
            className="grid gap-3"
          >
            {TEXT_FIELDS.map((f) => (
              <Field key={String(f.key)} label={f.label}>
                <Input
                  type={f.type ?? 'text'}
                  value={(form[f.key] as string | null) ?? ''}
                  onChange={(e) => setField(f.key, (e.target.value || null) as OrganizationCreate[typeof f.key])}
                  disabled={f.key === 'id'}
                />
              </Field>
            ))}

            {NUMBER_FIELDS.map((f) => (
              <Field key={String(f.key)} label={f.label}>
                <Input
                  type="number"
                  value={(form[f.key] as number | null) ?? ''}
                  onChange={(e) => {
                    const v = e.target.value === '' ? null : Number(e.target.value)
                    setField(f.key, v as OrganizationCreate[typeof f.key])
                  }}
                />
              </Field>
            ))}

            {DATE_FIELDS.map((f) => (
              <Field key={String(f.key)} label={f.label}>
                <Input
                  type="date"
                  value={(form[f.key] as string | null) ?? ''}
                  onChange={(e) => setField(f.key, (e.target.value || null) as OrganizationCreate[typeof f.key])}
                />
              </Field>
            ))}

            <div className="flex flex-wrap items-center gap-3 mt-3 pt-3 border-t border-slate-100">
              <Button type="submit" disabled={saveMut.isPending}>
                {saveMut.isPending ? 'Saving…' : 'Save'}
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={() => {
                  if (confirm(`ลบ ${orgId}?`)) deleteMut.mutate()
                }}
                disabled={deleteMut.isPending}
              >
                {deleteMut.isPending ? 'Deleting…' : 'Delete'}
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate({ to: '/organizations' })}>
                Back
              </Button>
              {savedAt && <span className="text-sm text-green-700">บันทึกแล้ว {savedAt}</span>}
              {saveMut.error && <ErrorMessage>{String(saveMut.error)}</ErrorMessage>}
              {deleteMut.error && <ErrorMessage>{String(deleteMut.error)}</ErrorMessage>}
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  )
}
