import React, { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BrainCircuit,
  Send,
  Trash2,
  Cloud,
} from "lucide-react";
import { PageHeader } from "@/components/common/PageHeader";
import { aiAnalystService } from "@/services/aiAnalyst.service";
import { AnalystMessage } from "../components/AnalystMessage";
import { useAIAnalyst } from "../hooks/useAIAnalyst";

// ─── Provider chip ────────────────────────────────────────────────────────────

function ProviderChip(): React.ReactElement {
  const { data, isLoading } = useQuery({
    queryKey: ["analyst-provider-status"],
    queryFn: aiAnalystService.getProviderStatus,
    staleTime: 10 * 60 * 1000,
    retry: false,
  });

  if (isLoading || !data) {
    return (
      <div className="h-7 w-32 rounded-full bg-slate-200 dark:bg-slate-700 animate-pulse" />
    );
  }

  const label = `Powered by ${data.primary.charAt(0).toUpperCase() + data.primary.slice(1)}`;
  const chipColor =
    data.primary === "groq"
      ? "bg-emerald-100 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-700"
      : data.primary === "gemini"
      ? "bg-blue-100 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-700"
      : "bg-violet-100 text-violet-700 border border-violet-200 dark:bg-violet-900/30 dark:text-violet-300 dark:border-violet-700";

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${chipColor}`}
      title={`Model: ${data.primary_model} | All cloud providers`}
    >
      <Cloud size={12} aria-hidden="true" />
      {label}
    </span>
  );
}

// ─── Suggested question chips ─────────────────────────────────────────────────

interface SuggestedChipsProps {
  onSelect: (question: string) => void;
  disabled: boolean;
}

function SuggestedChips({ onSelect, disabled }: SuggestedChipsProps): React.ReactElement {
  const { data } = useQuery({
    queryKey: ["analyst-suggested-questions"],
    queryFn: aiAnalystService.getSuggestedQuestions,
    staleTime: 6 * 60 * 60 * 1000,
  });

  if (!data?.questions.length) return <></>;

  return (
    <div
      className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-600"
      role="list"
      aria-label="Suggested questions"
    >
      {data.questions.map((q) => (
        <button
          key={q.id}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(q.text)}
          className="flex-shrink-0 text-xs px-3 py-1.5 rounded-full border
            border-slate-200 dark:border-slate-600
            bg-white dark:bg-slate-800
            text-slate-600 dark:text-slate-300
            hover:border-blue-400 hover:text-blue-600 dark:hover:text-blue-400
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors whitespace-nowrap"
          aria-label={`Ask: ${q.text}`}
        >
          {q.text}
        </button>
      ))}
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyChat(): React.ReactElement {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center px-4">
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-blue-600 flex items-center justify-center shadow-lg">
        <BrainCircuit size={32} className="text-white" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">
          Ask anything about your data
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 max-w-sm">
          I can analyse revenue trends, fraud activity, top merchants, category
          spend, KPIs, and account summaries — all grounded in your real data.
        </p>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AIAnalystPage(): React.ReactElement {
  const { ask, isLoading, messages, error, clearHistory } = useAIAnalyst();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  function handleSend(): void {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    ask(trimmed);
    setInput("");
    textareaRef.current?.focus();
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>): void {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <PageHeader
        title="AI Analyst"
        subtitle="Ask natural-language questions about your financial data."
        action={
          <div className="flex items-center gap-2">
            <ProviderChip />
            {hasMessages && (
              <button
                type="button"
                onClick={clearHistory}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg
                  border border-slate-200 dark:border-slate-600
                  text-slate-500 dark:text-slate-400
                  hover:border-red-300 hover:text-red-500 dark:hover:text-red-400
                  transition-colors"
                aria-label="Clear chat history"
              >
                <Trash2 size={13} aria-hidden="true" />
                Clear
              </button>
            )}
          </div>
        }
      />

      {/* Suggested question chips */}
      {!hasMessages && (
        <div className="mb-4">
          <SuggestedChips onSelect={(q) => { ask(q); }} disabled={isLoading} />
        </div>
      )}

      {/* Chat area */}
      <div className="flex-1 min-h-0 overflow-y-auto pr-1">
        {!hasMessages && !isLoading ? (
          <EmptyChat />
        ) : (
          <div className="max-w-3xl mx-auto py-2">
            {messages.map((msg, idx) => (
              <AnalystMessage
                key={msg.id}
                message={msg}
                isLastMessage={idx === messages.length - 1}
                isLoading={isLoading}
              />
            ))}
            {isLoading && messages[messages.length - 1]?.role === "ai" && (
              /* Typing indicator is shown inside AnalystMessage for user messages,
                 but guard against an AI message being the last one during loading */
              null
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div
          role="alert"
          className="mx-auto max-w-3xl w-full mb-3 px-4 py-2 rounded-lg
            bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800
            text-sm text-red-700 dark:text-red-300"
        >
          {error instanceof Error ? error.message : "An error occurred. Please try again."}
        </div>
      )}

      {/* Input bar */}
      <div className="border-t border-slate-200 dark:border-slate-700 pt-4 mt-2">
        <div className="max-w-3xl mx-auto">
          {hasMessages && (
            <div className="mb-2">
              <SuggestedChips onSelect={(q) => { setInput(q); textareaRef.current?.focus(); }} disabled={isLoading} />
            </div>
          )}
          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              placeholder="Ask about revenue, fraud, merchants, KPIs…"
              disabled={isLoading}
              aria-label="Question input"
              className="flex-1 resize-none rounded-xl border border-slate-200 dark:border-slate-600
                bg-white dark:bg-slate-800
                text-sm text-slate-800 dark:text-slate-200
                placeholder:text-slate-400 dark:placeholder:text-slate-500
                px-4 py-3 min-h-[48px] max-h-[160px]
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                disabled:opacity-60 disabled:cursor-not-allowed
                transition-all overflow-y-auto"
              style={{ fieldSizing: "content" } as React.CSSProperties}
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              aria-label="Send question"
              className="flex-shrink-0 w-11 h-11 rounded-xl
                bg-blue-600 hover:bg-blue-700
                disabled:bg-slate-200 dark:disabled:bg-slate-700
                disabled:cursor-not-allowed
                flex items-center justify-center
                transition-colors shadow-sm"
            >
              <Send
                size={18}
                className={isLoading || !input.trim()
                  ? "text-slate-400 dark:text-slate-500"
                  : "text-white"
                }
                aria-hidden="true"
              />
            </button>
          </div>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-2 text-center">
            Press <kbd className="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-700 font-mono text-xs">Enter</kbd> to send
            · <kbd className="px-1 py-0.5 rounded bg-slate-100 dark:bg-slate-700 font-mono text-xs">Shift+Enter</kbd> for new line
          </p>
        </div>
      </div>
    </div>
  );
}
