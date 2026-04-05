import { useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Plus, Trash2, CheckCircle2, AlertCircle, Loader2, UserPlus } from "lucide-react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/Button";
import { authService } from "@/services/auth.service";
import useWizardStore from "@/stores/wizard.store";
import type { InviteEntry } from "@/types/wizard.types";

const MAX_INVITES = 10;

function createEntry(): InviteEntry {
  return {
    id: crypto.randomUUID(),
    email: "",
    role: "analyst",
    status: "pending",
  };
}

export function Step4InviteTeam() {
  const { data, updateData, goNext, goBack, isSubmitting, setSubmitting } = useWizardStore();
  const [entries, setEntries] = useState<InviteEntry[]>(
    data.invites.length > 0 ? data.invites : [createEntry()]
  );
  const [emailErrors, setEmailErrors] = useState<Record<string, string>>({});

  const updateEntry = useCallback(
    (id: string, patch: Partial<InviteEntry>) => {
      setEntries((prev) =>
        prev.map((e) => (e.id === id ? { ...e, ...patch } : e))
      );
    },
    []
  );

  const addEntry = () => {
    if (entries.length < MAX_INVITES) {
      setEntries((prev) => [...prev, createEntry()]);
    }
  };

  const removeEntry = (id: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== id));
    setEmailErrors((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const validateEmails = (): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const errors: Record<string, string> = {};
    const seen = new Set<string>();

    entries.forEach((e) => {
      if (!e.email.trim()) {
        errors[e.id] = "Email is required";
      } else if (!emailRegex.test(e.email.trim())) {
        errors[e.id] = "Enter a valid email address";
      } else if (seen.has(e.email.trim().toLowerCase())) {
        errors[e.id] = "Duplicate email";
      } else {
        seen.add(e.email.trim().toLowerCase());
      }
    });

    setEmailErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    // Allow skipping — no invites required
    if (entries.length === 1 && !entries[0].email.trim()) {
      updateData({ invites: [] });
      goNext();
      return;
    }

    if (!validateEmails()) return;

    setSubmitting(true);

    const settled = await Promise.allSettled(
      entries.map(async (entry) => {
        try {
          await authService.inviteUser({
            email: entry.email.trim(),
            full_name: entry.email.split("@")[0],
            role: entry.role,
            // Temporary password — user must reset on first login
            password: crypto.randomUUID().slice(0, 16),
          });
          return { id: entry.id, status: "sent" as const };
        } catch {
          return { id: entry.id, status: "error" as const };
        }
      })
    );

    const updated = entries.map((e) => {
      const result = settled.find(
        (r) => r.status === "fulfilled" && r.value.id === e.id
      );
      return result?.status === "fulfilled"
        ? { ...e, status: result.value.status }
        : { ...e, status: "error" as const };
    });

    setEntries(updated);
    updateData({ invites: updated });
    setSubmitting(false);

    // Proceed if at least one succeeded (or all had errors — allow skipping past)
    goNext();
  };

  return (
    <div className="max-w-lg mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Invite your team
        </h1>
        <p className="mt-2 text-slate-500 dark:text-slate-400">
          Add teammates now or skip — you can always invite people later from settings.
        </p>
      </div>

      <div className="space-y-3">
        <AnimatePresence initial={false}>
          {entries.map((entry, idx) => (
            <motion.div
              key={entry.id}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: -20, height: 0 }}
              transition={{ duration: 0.25, ease: [0.25, 0.1, 0.25, 1.0] }}
              className="overflow-hidden"
            >
              <div
                className={cn(
                  "flex items-start gap-2 p-3 rounded-xl border transition-colors",
                  emailErrors[entry.id]
                    ? "border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/10"
                    : "border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50"
                )}
              >
                {/* Status icon */}
                <div className="flex-shrink-0 mt-2.5">
                  {entry.status === "sent" && (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" aria-label="Invite sent" />
                  )}
                  {entry.status === "error" && (
                    <AlertCircle className="w-4 h-4 text-red-500" aria-label="Invite failed" />
                  )}
                  {entry.status === "pending" && (
                    <UserPlus className="w-4 h-4 text-slate-400" aria-hidden="true" />
                  )}
                </div>

                {/* Email */}
                <div className="flex-1 min-w-0">
                  <input
                    type="email"
                    value={entry.email}
                    onChange={(e) => updateEntry(entry.id, { email: e.target.value })}
                    placeholder={`teammate${idx + 1}@company.com`}
                    aria-label={`Email for invite ${idx + 1}`}
                    aria-invalid={!!emailErrors[entry.id]}
                    disabled={entry.status === "sent"}
                    className={cn(
                      "w-full bg-transparent text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400",
                      "focus:outline-none disabled:opacity-60",
                      entry.status === "sent" && "line-through"
                    )}
                  />
                  <AnimatePresence>
                    {emailErrors[entry.id] && (
                      <motion.p
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="text-red-500 text-xs overflow-hidden mt-0.5"
                        role="alert"
                      >
                        {emailErrors[entry.id]}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                {/* Role selector */}
                <select
                  value={entry.role}
                  onChange={(e) =>
                    updateEntry(entry.id, {
                      role: e.target.value as InviteEntry["role"],
                    })
                  }
                  disabled={entry.status === "sent"}
                  aria-label={`Role for invite ${idx + 1}`}
                  className={cn(
                    "text-xs rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-2 py-1.5",
                    "focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-60 flex-shrink-0"
                  )}
                >
                  <option value="analyst">Analyst</option>
                  <option value="viewer">Viewer</option>
                </select>

                {/* Remove */}
                {entries.length > 1 && entry.status !== "sent" && (
                  <button
                    type="button"
                    onClick={() => removeEntry(entry.id)}
                    aria-label={`Remove invite ${idx + 1}`}
                    className="flex-shrink-0 mt-1 p-1 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>
                )}

                {/* Pending spinner */}
                {isSubmitting && entry.status === "pending" && (
                  <Loader2
                    className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0 mt-1.5"
                    aria-label="Sending invite"
                  />
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Add more */}
        {entries.length < MAX_INVITES && (
          <button
            type="button"
            onClick={addEntry}
            className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-md px-1"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            Add another
          </button>
        )}
      </div>

      {/* CTA */}
      <div className="flex justify-between pt-6">
        <Button type="button" variant="outline" size="lg" onClick={goBack}>
          Back
        </Button>
        <div className="flex gap-3">
          <Button
            type="button"
            variant="ghost"
            size="lg"
            onClick={() => { updateData({ invites: [] }); goNext(); }}
          >
            Skip
          </Button>
          <Button
            type="button"
            size="lg"
            loading={isSubmitting}
            onClick={handleSubmit}
          >
            Send invites
          </Button>
        </div>
      </div>
    </div>
  );
}
