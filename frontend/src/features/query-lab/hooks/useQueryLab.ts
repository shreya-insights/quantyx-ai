import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryLabService } from "@/services/queryLab.service";

export function useQueryTemplates() {
  return useQuery({
    queryKey: ["query-templates"],
    queryFn: () => queryLabService.getTemplates(),
    staleTime: Infinity, // Templates don't change
  });
}

export function useSavedQueries() {
  return useQuery({
    queryKey: ["saved-queries"],
    queryFn: () => queryLabService.getSavedQueries(),
    staleTime: 30_000,
  });
}

export function useExecuteQuery() {
  return useMutation({
    mutationFn: ({ sql, limit }: { sql: string; limit?: number }) =>
      queryLabService.execute(sql, limit),
  });
}

export function useSaveQuery() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; description?: string; query_text: string; is_public?: boolean }) =>
      queryLabService.saveQuery(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saved-queries"] });
    },
  });
}

export function useDeleteQuery() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => queryLabService.deleteQuery(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saved-queries"] });
    },
  });
}
