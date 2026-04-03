import { lazy, Suspense, useState, useCallback } from "react";
import { Play, Save, X, Terminal } from "lucide-react";
import {
  useQueryTemplates,
  useSavedQueries,
  useExecuteQuery,
  useSaveQuery,
  useDeleteQuery,
} from "../hooks/useQueryLab";
import { Button, Modal, Spinner, Input } from "@/components/ui";
import { PageHeader } from "@/components/common/PageHeader";
import { useThemeStore } from "@/stores/theme.store";
import type { QueryResult } from "@/types/api.types";

const MonacoEditor = lazy(() => import("@monaco-editor/react"));

const INITIAL_SQL = `-- Quantyx AI · Query Lab
-- Write SELECT queries on your financial data
-- All queries are scoped to your tenant automatically

SELECT
    DATE_FORMAT(transaction_date, '%Y-%m') AS month,
    COUNT(*) AS total_transactions,
    ROUND(SUM(amount), 2) AS total_volume,
    ROUND(AVG(amount), 2) AS avg_amount
FROM transactions
WHERE status = 'completed'
GROUP BY month
ORDER BY month DESC
LIMIT 12;`;

const CATEGORY_COLORS: Record<string, string> = {
  Revenue:    "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  Customer:   "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
  Merchants:  "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  Fraud:      "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
  Operations: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  Accounts:   "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300",
};

export default function QueryLabPage() {
  const { theme }              = useThemeStore();
  const [sql, setSql]          = useState(INITIAL_SQL);
  const [result, setResult]    = useState<QueryResult | null>(null);
  const [activePanel, setPanel]  = useState<"templates" | "saved">("templates");
  const [showSave, setShowSave]  = useState(false);
  const [saveName, setSaveName]  = useState("");

  const templatesQuery  = useQueryTemplates();
  const savedQuery      = useSavedQueries();
  const executeMutation = useExecuteQuery();
  const saveMutation    = useSaveQuery();
  const deleteMutation  = useDeleteQuery();

  const runQuery = useCallback(() => {
    setResult(null);
    executeMutation.mutate(
      { sql, limit: 500 },
      { onSuccess: (data) => setResult(data) }
    );
  }, [sql, executeMutation]);

  const handleSave = () => {
    if (!saveName.trim()) return;
    saveMutation.mutate(
      { name: saveName, query_text: sql, is_public: false },
      { onSuccess: () => { setShowSave(false); setSaveName(""); } }
    );
  };

  const errorMsg = executeMutation.isError
    ? ((executeMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Query execution failed")
    : null;

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* ── Left panel: templates + saved ── */}
      <aside
        aria-label="Query templates and saved queries"
        className="w-full lg:w-72 border-b lg:border-b-0 lg:border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex flex-col flex-shrink-0 max-h-48 lg:max-h-none"
      >
        <div className="p-4 border-b border-slate-100 dark:border-slate-700">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100">Query Lab</h2>
          <p className="text-xs text-slate-400 mt-0.5">Safe SELECT sandbox · Max 500 rows</p>
        </div>

        <div className="flex border-b border-slate-100 dark:border-slate-700">
          {(["templates", "saved"] as const).map((p) => (
            <button
              key={p}
              role="tab"
              aria-selected={activePanel === p}
              onClick={() => setPanel(p)}
              className={`flex-1 py-2 text-xs font-medium capitalize transition-colors ${
                activePanel === p ? "text-brand-600 border-b-2 border-brand-600" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              }`}
            >
              {p} {p === "saved" && `(${savedQuery.data?.length ?? 0})`}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {activePanel === "templates" && templatesQuery.data?.map((t) => (
            <button
              key={t.id}
              onClick={() => setSql(t.query_text)}
              className="w-full text-left p-3 rounded-lg border border-slate-100 dark:border-slate-700 hover:border-brand-200 dark:hover:border-brand-700 hover:bg-brand-50 dark:hover:bg-brand-900/10 transition-colors group"
            >
              <span className={`text-xs px-1.5 py-0.5 rounded font-medium mb-1.5 inline-block ${CATEGORY_COLORS[t.category] ?? ""}`}>
                {t.category}
              </span>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300 group-hover:text-brand-700 dark:group-hover:text-brand-400">{t.name}</p>
              <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{t.description}</p>
            </button>
          ))}

          {activePanel === "saved" && (
            savedQuery.data?.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-sm">
                <p>No saved queries</p>
                <p className="text-xs mt-1">Run a query and save it</p>
              </div>
            ) : (
              savedQuery.data?.map((q) => (
                <div key={q.id} className="group p-3 rounded-lg border border-slate-100 dark:border-slate-700 hover:border-brand-200 dark:hover:border-brand-700">
                  <div className="flex items-start justify-between gap-1">
                    <button onClick={() => setSql(q.query_text)} className="flex-1 text-left text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-brand-600 dark:hover:text-brand-400">
                      {q.name}
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(q.id)}
                      aria-label={`Delete query "${q.name}"`}
                      className="text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded"
                    >
                      <X size={13} aria-hidden="true" />
                    </button>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">Run {q.execution_count}&times;</p>
                </div>
              ))
            )
          )}
        </div>
      </aside>

      {/* ── Main: editor + results ── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-4 py-2.5 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex-shrink-0">
          <Button
            onClick={runQuery}
            loading={executeMutation.isPending}
            leftIcon={<Play size={13} aria-hidden="true" />}
            size="sm"
          >
            Run Query
          </Button>
          <span className="text-slate-300 dark:text-slate-600" aria-hidden="true">|</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowSave(true)}
            leftIcon={<Save size={13} aria-hidden="true" />}
          >
            Save
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setResult(null); executeMutation.reset(); }}
            leftIcon={<X size={13} aria-hidden="true" />}
          >
            Clear
          </Button>
          {result && (
            <span className="ml-auto text-xs text-slate-400">
              {result.row_count} rows · {result.execution_time_ms.toFixed(1)}ms
              {result.truncated && " · truncated"}
            </span>
          )}
        </div>

        {/* Monaco Editor */}
        <div className="h-48 sm:h-64 lg:h-[calc(30vh)] border-b border-slate-200 dark:border-slate-700 flex-shrink-0">
          <Suspense fallback={<div className="h-full flex items-center justify-center"><Spinner /></div>}>
            <MonacoEditor
              value={sql}
              onChange={(v) => setSql(v ?? "")}
              language="sql"
              theme={theme === "dark" ? "vs-dark" : "vs"}
              options={{
                fontSize: 13,
                lineNumbers: "on",
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: "on",
                tabSize: 2,
                fontFamily: "JetBrains Mono, Fira Code, monospace",
                renderLineHighlight: "line",
              }}
            />
          </Suspense>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-auto bg-slate-50 dark:bg-slate-900">
          {errorMsg && (
            <div className="m-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 rounded-lg p-4 text-sm">
              <strong>Error:</strong> {errorMsg}
            </div>
          )}

          {result && result.row_count === 0 && (
            <div className="m-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-8 text-center text-slate-400">
              Query returned 0 rows.
            </div>
          )}

          {result && result.row_count > 0 && (
            <table className="w-full text-sm">
              <caption className="sr-only">Query results — {result.row_count} rows</caption>
              <thead className="sticky top-0 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <tr>
                  {result.columns.map((col) => (
                    <th key={col} scope="col" className="text-left py-2.5 px-4 text-xs font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-slate-900">
                {result.rows.map((row, i) => (
                  <tr key={i} className="border-b border-slate-50 dark:border-slate-800 hover:bg-brand-50 dark:hover:bg-brand-900/10">
                    {(row as unknown[]).map((cell, j) => (
                      <td key={j} className="py-2 px-4 text-slate-700 dark:text-slate-300 whitespace-nowrap font-mono text-xs">
                        {cell === null ? <span className="text-slate-300 dark:text-slate-600 italic">NULL</span> : String(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {!result && !errorMsg && !executeMutation.isPending && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-sm px-4">
                <div className="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto mb-4">
                  <Terminal size={30} strokeWidth={1.5} className="text-slate-400 dark:text-slate-500" aria-hidden="true" />
                </div>
                <p className="text-base font-semibold text-slate-700 dark:text-slate-300">Ready to query</p>
                <p className="text-sm mt-1.5 text-slate-400 dark:text-slate-500 leading-relaxed">
                  Select a template from the left panel or write your own SQL. Only SELECT statements are allowed — max 500 rows, auto-scoped to your tenant.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Save Modal */}
      <Modal open={showSave} onClose={() => { setShowSave(false); setSaveName(""); }} title="Save Query" size="sm">
        <div className="space-y-4">
          <Input
            label="Query name"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            placeholder="My revenue query"
            autoFocus
          />
          <div className="flex gap-2">
            <Button onClick={handleSave} loading={saveMutation.isPending} className="flex-1">Save</Button>
            <Button variant="outline" onClick={() => { setShowSave(false); setSaveName(""); }} className="flex-1">Cancel</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
