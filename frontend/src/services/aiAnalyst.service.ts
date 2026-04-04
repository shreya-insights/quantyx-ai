import { api } from "@/lib/axios";

export interface AnalystAskRequest {
  question: string;
}

export interface AnalystAskResponse {
  answer: string;
  confidence: "high" | "medium" | "low";
  caveats: string[];
  chart_suggestion: string | null;
  provider: string;
  model: string;
  latency_ms: number;
  tools_used: string[];
}

export interface SuggestedQuestion {
  id: string;
  text: string;
  category: string;
}

export interface SuggestedQuestionsResponse {
  questions: SuggestedQuestion[];
}

export interface ProviderStatusResponse {
  primary: string;
  primary_model: string;
  fallback: string;
  fallback_model: string;
  tertiary: string;
  tertiary_model: string;
  all_cloud: boolean;
  local_model: boolean;
}

export const aiAnalystService = {
  ask: (question: string): Promise<AnalystAskResponse> =>
    api
      .post<AnalystAskResponse>("/analyst/ask", { question })
      .then((r) => r.data),

  getSuggestedQuestions: (): Promise<SuggestedQuestionsResponse> =>
    api
      .get<SuggestedQuestionsResponse>("/analyst/suggested-questions")
      .then((r) => r.data),

  getProviderStatus: (): Promise<ProviderStatusResponse> =>
    api
      .get<ProviderStatusResponse>("/analyst/provider-status")
      .then((r) => r.data),
};
