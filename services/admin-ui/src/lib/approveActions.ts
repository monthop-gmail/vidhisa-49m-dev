import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export function useApproveRecord() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ recordId, approvedBy }: { recordId: number; approvedBy: string }) => {
      const { data, error } = await api.PATCH('/api/records/{record_id}/approve', {
        params: { path: { record_id: recordId } },
        body: { approved_by: approvedBy },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => invalidateAll(qc),
  })
}

export function useRejectRecord() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ recordId, reason }: { recordId: number; reason: string }) => {
      const { data, error } = await api.PATCH('/api/records/{record_id}/reject', {
        params: { path: { record_id: recordId } },
        body: { reason },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => invalidateAll(qc),
  })
}

export function useApproveOrg() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (orgId: string) => {
      const { data, error } = await api.PATCH('/api/organizations/{org_id}/approve', {
        params: { path: { org_id: orgId } },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => invalidateAll(qc),
  })
}

export function useRejectOrg() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (orgId: string) => {
      const { data, error } = await api.PATCH('/api/organizations/{org_id}/reject', {
        params: { path: { org_id: orgId } },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => invalidateAll(qc),
  })
}

export function useApproveParticipant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (participantId: number) => {
      const { data, error } = await api.PATCH('/api/participants/{participant_id}/approve', {
        params: { path: { participant_id: participantId } },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => invalidateAll(qc),
  })
}

export function useRejectParticipant() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (participantId: number) => {
      const { data, error } = await api.PATCH('/api/participants/{participant_id}/reject', {
        params: { path: { participant_id: participantId } },
      })
      if (error) throw error
      return data
    },
    onSuccess: () => invalidateAll(qc),
  })
}

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['records'] })
  qc.invalidateQueries({ queryKey: ['branch-pending'] })
  qc.invalidateQueries({ queryKey: ['organizations'] })
  qc.invalidateQueries({ queryKey: ['organizations-pending'] })
  qc.invalidateQueries({ queryKey: ['participants'] })
  qc.invalidateQueries({ queryKey: ['participants-pending'] })
}
