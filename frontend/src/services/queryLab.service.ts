import { api } from "@/lib/axios";
import type { QueryResult, QueryTemplate, SavedQuery } from "@/types/api.types";

export const queryLabService = {
  execute: (sql: string, limit = 500) =>
    api
      .post<QueryResult>("/query-lab/execute", { sql, limit })
      .then((r) => r.data),

  getTemplates: () =>
    api.get<QueryTemplate[]>("/query-lab/templates").then((r) => r.data),

  getSavedQueries: () =>
    api.get<SavedQuery[]>("/query-lab/saved").then((r) => r.data),

  saveQuery: (payload: {
    name: string;
    description?: string;
    query_text: string;
    is_public?: boolean;
  }) => api.post<SavedQuery>("/query-lab/saved", payload).then((r) => r.data),

  deleteQuery: (id: number) =>
    api.delete(`/query-lab/saved/${id}`),
};
