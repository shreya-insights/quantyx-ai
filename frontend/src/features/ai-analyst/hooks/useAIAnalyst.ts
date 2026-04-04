import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  aiAnalystService,
  type AnalystAskResponse,
} from "@/services/aiAnalyst.service";

export type ChatMessageRole = "user" | "ai";

export interface UserChatMessage {
  role: "user";
  id: string;
  text: string;
  timestamp: Date;
}

export interface AIChatMessage {
  role: "ai";
  id: string;
  timestamp: Date;
  answer: string;
  confidence: "high" | "medium" | "low";
  caveats: string[];
  chart_suggestion: string | null;
  provider: string;
  model: string;
  latency_ms: number;
  tools_used: string[];
}

export type ChatMessage = UserChatMessage | AIChatMessage;

let _messageCounter = 0;
function nextId(): string {
  return `msg_${Date.now()}_${++_messageCounter}`;
}

export function useAIAnalyst() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const mutation = useMutation({
    mutationFn: (question: string) => aiAnalystService.ask(question),
    onSuccess: (data: AnalystAskResponse) => {
      const aiMessage: AIChatMessage = {
        role: "ai",
        id: nextId(),
        timestamp: new Date(),
        answer: data.answer,
        confidence: data.confidence,
        caveats: data.caveats,
        chart_suggestion: data.chart_suggestion,
        provider: data.provider,
        model: data.model,
        latency_ms: data.latency_ms,
        tools_used: data.tools_used,
      };
      setMessages((prev) => [...prev, aiMessage]);
    },
  });

  function ask(question: string): void {
    const trimmed = question.trim();
    if (!trimmed) return;

    const userMessage: UserChatMessage = {
      role: "user",
      id: nextId(),
      text: trimmed,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    mutation.mutate(trimmed);
  }

  function clearHistory(): void {
    setMessages([]);
    mutation.reset();
  }

  return {
    ask,
    isLoading: mutation.isPending,
    messages,
    error: mutation.error,
    clearHistory,
  };
}
