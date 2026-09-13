import { LoaderCircle, Search } from "lucide-react"
import { useState, type ChangeEvent, type FormEvent } from "react"
import { toast } from "sonner"

import { BorderBeam } from "@/components/ui/border-beam"
import { Button } from "@/components/ui/button"
import { Field, inputClass } from "@/components/ui/field"
import { navigate } from "@/hooks/useHashRoute"
import { applyDraft, draftFromProfile, validateDraft, type ContextDraft, type DraftErrors } from "@/lib/profile-edit"
import type { MolecularProfile } from "@/lib/types"
import { useCase } from "@/state/case-store"

const ECOG_OPTIONS = ["0", "1", "2", "3", "4", "5"]

export function ContextForm({ profile }: { profile: MolecularProfile }) {
  const { contextDraft, setContextDraft, editProfile, runMatch, busy, results, isStale } = useCase()
  const draft = contextDraft ?? draftFromProfile(profile)
  const [errors, setErrors] = useState<DraftErrors>({})
  const [confirmed, setConfirmed] = useState(false)
  const searching = busy === "match"

  const update = (key: keyof ContextDraft) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    { setContextDraft({ ...draft, [key]: event.target.value }); setConfirmed(false) }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const found = validateDraft(draft)
    setErrors(found)
    if (Object.keys(found).length) return
    const reviewed = applyDraft(profile, draft)
    editProfile(reviewed)
    if (await runMatch(reviewed)) {
      toast.success("Evidence and trials retrieved.")
      navigate("overview")
    }
  }

  const submitLabel = results ? (isStale ? "Re-run search with edits" : "Search again") : "Find evidence and trials"

  return (
    <form onSubmit={submit} noValidate className="grid gap-5 px-6 pb-6">
      <Field label="Diagnosis" error={errors.diagnosis}>
        {(control) => <input {...control} className={inputClass} value={draft.diagnosis} onChange={update("diagnosis")} maxLength={200} />}
      </Field>

      <Field label="Patient city (optional)" error={errors.city}>
        {(control) => <input {...control} className={inputClass} value={draft.city} onChange={update("city")} placeholder="e.g. Singapore or Boston, MA" maxLength={120} />}
      </Field>

      <p className="text-xs text-muted-foreground">Leave unrecorded clinical fields unknown. Missing MSI, ECOG or treatment history does not establish eligibility; matching can still proceed.</p>
      <details open className="rounded-xl border border-border bg-card-2 p-4">
        <summary className="cursor-pointer text-sm font-medium">Optional clinical context</summary>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="MSI (optional)">{control => <select {...control} className={inputClass} value={draft.msi} onChange={update("msi")}>{[...new Set(["", "high", "stable", "not_detected", "indeterminate", draft.msi])].map(x => <option key={x} value={x}>{x.replaceAll("_", " ") || "Unknown"}</option>)}</select>}</Field>
          <Field label="Stage (optional)">{control => <input {...control} className={inputClass} value={draft.stage} onChange={update("stage")} maxLength={80} placeholder="Unknown" />}</Field>
          <Field label="Country" error={errors.country}>
            {(control) => <input {...control} className={inputClass} value={draft.country} onChange={update("country")} placeholder="Optional" maxLength={80} />}
          </Field>
          <Field label="Age (years)" error={errors.age}>
            {(control) => <input {...control} className={inputClass} value={draft.age} onChange={update("age")} inputMode="numeric" placeholder="Optional" maxLength={3} />}
          </Field>
          <Field label="ECOG performance status">
          {(control) => (
            <select {...control} className={inputClass} value={draft.ecog} onChange={update("ecog")}>
              <option value="">Unknown</option>
              {ECOG_OPTIONS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          )}
          </Field>
          <Field label="Treatment history (optional)">{control => <select {...control} className={inputClass} value={draft.therapyStatus} onChange={update("therapyStatus")}><option value="unknown">Unknown</option><option value="none">Confirmed no prior treatments</option><option value="entered">Treatments entered</option></select>}</Field>
          {draft.therapyStatus === "entered" && <Field label="Previous treatments" error={errors.therapies} hint="Comma-separated.">
            {(control) => <input {...control} className={inputClass} value={draft.therapies} onChange={update("therapies")} maxLength={300} />}
          </Field>}
        </div>
      </details>

      <p className="text-xs text-muted-foreground">Location is optional. Clearing the city leaves geographic access unknown. Unchanged selected cities retain their coordinates; edited cities are resolved server-side.</p>

      <Button type="button" variant="outline" disabled={searching} onClick={() => { const found = validateDraft(draft); setErrors(found); if (!Object.keys(found).length) { editProfile(applyDraft(profile, draft)); setConfirmed(false); toast.success("Profile context saved.") } }}>Save context without matching</Button>
      <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-card-2 p-4 text-sm transition-colors hover:border-border-strong has-checked:border-primary/40 has-checked:bg-primary/6">
        <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} className="mt-0.5 size-4 accent-[var(--color-primary)]" />
        <span>I reviewed the diagnosis, biomarkers and optional patient context.</span>
      </label>

      <Button type="submit" size="lg" disabled={!confirmed || searching} className="relative overflow-hidden">
        {searching && <BorderBeam size={90} duration={3} colorFrom="var(--color-primary-foreground)" colorTo="white" />}
        {searching ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Search aria-hidden="true" />}
        {searching ? "Running ASTRA and ranking open sites…" : submitLabel}
      </Button>
    </form>
  )
}
