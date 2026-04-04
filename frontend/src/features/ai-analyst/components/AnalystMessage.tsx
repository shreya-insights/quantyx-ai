import React from "react";
import { AlertTriangle, Zap } from "lucide-react";
import type { AIChatMessage, ChatMessage, UserChatMessage } from "../hooks/useAIAnalyst";

// ─── Confidence styling map ───────────────────────────────────────────────────

const CONFIDENCE_BORDER: Record<"high" | "medium" | "low", string> = {
  high: "border-l-emerald-500",
  medium: "border-l-amber-400",
  low: "border-l-slate-400",
};

const CONFIDENCE_BADGE: Record<"high" | "medium" | "low", string> = {
  high: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  low: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
};

// ─── Typing indicator ─────────────────────────────────────────────────────────

function TypingIndicator(): React.ReactElement {
  return (
    <div className="flex items-start gap-3 mb-4">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-blue-600 flex items-center justify-center">
        <Zap size={14} className="text-white" />
      </div>
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
        <div className="flex gap-1 items-center h-5">
          <span
            className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce"
            style={{ animationDelay: "0ms" }}
          />
          <span
            className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce"
            style={{ animationDelay: "150ms" }}
          />
          <span
            className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce"
            style={{ animationDelay: "300ms" }}
          />
        </div>
      </div>
    </div>
  );
}

// ─── User bubble ──────────────────────────────────────────────────────────────

function UserMessage({ message }: { message: UserChatMessage }): React.ReactElement {
  return (
    <div className="flex justify-end mb-4">
      <div className="max-w-[75%]">
        <div className="bg-blue-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm shadow-sm">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.text}</p>
        </div>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 text-right">
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}

// ─── AI bubble ────────────────────────────────────────────────────────────────

function AIMessage({ message }: { message: AIChatMessage }): React.ReactElement {
  return (
    <div className="flex items-start gap-3 mb-4">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-blue-600 flex items-center justify-center">
        <Zap size={14} className="text-white" />
      </div>

      <div className="max-w-[85%] min-w-0">
        <div
          className={`relative bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700
            border-l-4 ${CONFIDENCE_BORDER[message.confidence]}
            rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm`}
        >
          {/* Confidence badge */}
          <span
            className={`absolute top-2 right-3 text-xs font-medium px-2 py-0.5 rounded-full
              ${CONFIDENCE_BADGE[message.confidence]}`}
          >
            {message.confidence}
          </span>

          {/* Answer text */}
          <p className="text-sm leading-relaxed text-slate-800 dark:text-slate-200 pr-16 whitespace-pre-wrap">
            {message.answer}
          </p>

          {/* Caveats */}
          {message.caveats.length > 0 && (
            <div className="mt-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-3 py-2">
              <div className="flex items-center gap-1.5 mb-1">
                <AlertTriangle size={12} className="text-amber-600 dark:text-amber-400 flex-shrink-0" />
                <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">
                  Caveats
                </span>
              </div>
              <ul className="space-y-0.5">
                {message.caveats.map((caveat, idx) => (
                  <li key={idx} className="text-xs text-amber-700 dark:text-amber-300">
                    • {caveat}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tools used */}
          {message.tools_used.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {message.tools_used.map((tool) => (
                <span
                  key={tool}
                  className="inline-block text-xs px-2 py-0.5 rounded-full
                    bg-violet-100 text-violet-700
                    dark:bg-violet-900/30 dark:text-violet-300"
                >
                  {tool.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-2 mt-1 ml-1">
          <p className="text-xs text-slate-400 dark:text-slate-500">
            {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </p>
          <span className="text-xs text-slate-300 dark:text-slate-600">·</span>
          <p className="text-xs text-slate-400 dark:text-slate-500">
            {message.provider} · {message.latency_ms.toFixed(0)}ms
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Public component ─────────────────────────────────────────────────────────

interface AnalystMessageProps {
  message: ChatMessage;
  isLastMessage: boolean;
  isLoading: boolean;
}

export function AnalystMessage({
  message,
  isLastMessage,
  isLoading,
}: AnalystMessageProps): React.ReactElement {
  if (message.role === "user") {
    return (
      <>
        <UserMessage message={message} />
        {isLastMessage && isLoading && <TypingIndicator />}
      </>
    );
  }
  return <AIMessage message={message} />;
}
