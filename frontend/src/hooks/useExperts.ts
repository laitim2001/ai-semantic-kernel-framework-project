/**
 * React Query hooks for Agent Expert CRUD operations.
 *
 * Sprint 164 — Phase 46 Agent Expert Registry.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  expertsApi,
  type CreateExpertRequest,
  type UpdateExpertRequest,
} from '@/api/endpoints/experts';

const EXPERTS_KEY = ['experts'] as const;

export function useExpertsList(domain?: string, enabled?: boolean) {
  return useQuery({
    queryKey: [...EXPERTS_KEY, { domain, enabled }],
    queryFn: () => expertsApi.list(domain, enabled),
  });
}

export function useExpertDetail(name: string) {
  return useQuery({
    queryKey: [...EXPERTS_KEY, name],
    queryFn: () => expertsApi.get(name),
    enabled: !!name,
  });
}

export function useCreateExpert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateExpertRequest) => expertsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: EXPERTS_KEY });
    },
  });
}

export function useUpdateExpert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, data }: { name: string; data: UpdateExpertRequest }) =>
      expertsApi.update(name, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: EXPERTS_KEY });
      queryClient.invalidateQueries({ queryKey: [...EXPERTS_KEY, variables.name] });
    },
  });
}

export function useDeleteExpert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => expertsApi.delete(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: EXPERTS_KEY });
    },
  });
}

export function useReloadExperts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => expertsApi.reload(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: EXPERTS_KEY });
    },
  });
}
