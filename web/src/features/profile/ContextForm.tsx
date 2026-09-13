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

const OPTIONAL_FIELDS: { key: keyof ContextDraft; label: string; inputMode?: "decimal" | "numeric"; placeholder: string }[] = [
  { key: "city", label: "City", placeholder: "Optional" },
  { key: "country", label: "Country", placeholder: "Optional" },
  { key: "latitude", label: "Latitude", inputMode: "decimal", placeholder: "e.g. 1.3521" },
  { key: "longitude", label: "Longitude", inputMode: "decimal", placeholder: "e.g. 103.8198" },
  { key: "age", label: "Age (years)", inputMode: "numeric", placeholder: "Optional" },
]
const ECOG_OPTIONS = ["0", "1", "2", "3", "4", "5"]

export function ContextForm({ profile }: { profile: MolecularProfile }) {
  const { editProfile, runMatch, busy, results, isStale } = useCase()
  const [draft, setDraft] = useState(() => draftFromProfile(profile))
  const [errors, setErrors] = useState<DraftErrors>({})
  const [confirmed, setConfirmed] = useState(false)
  const searching = busy === "match"

  const update = (key: keyof ContextDraft) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setDraft((current) => ({ ...current, [key]: event.target.value }))

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

      <div className="grid gap-4 sm:grid-cols-2">
        {OPTIONAL_FIELDS.map((field) => (
          <Field key={field.key} label={field.label} error={errors[field.key]}>
            {(control) => (
              <input
                {...control}
                className={inputClass}
                value={draft[field.key]}
                onChange={update(field.key)}
                inputMode={field.inputMode}
                placeholder={field.placeholder}
                maxLength={80}
              />
            )}
          </Field>
        ))}
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
      </div>

      <Field label="Previous treatments" hint="Comma-separated. Blank means unrecorded, not treatment-naive.">
        {(control) => <input {...control} className={inputClass} value={draft.therapies} onChange={update("therapies")} maxLength={300} />}
      </Field>

      <p className="text-xs text-muted-foreground">City and country alone do not calculate distance. Add coordinates to rank nearby sites.</p>

      <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-card-2 p-4 text-sm transition-colors hover:border-border-strong has-checked:border-primary/40 has-checked:bg-primary/6">
        <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} className="mt-0.5 size-4 accent-[var(--color-primary)]" />
        <span>I reviewed the diagnosis, biomarkers and optional patient context.</span>
      </label>

      <Button type="submit" size="lg" disabled={!confirmed || searching} className="relative overflow-hidden">
        {searching && <BorderBeam size={90} duration={3} colorFrom="var(--color-primary-foreground)" colorTo="white" />}
        {searching ? <LoaderCircle className="animate-spin" aria-hidden="true" /> : <Search aria-hidden="true" />}
        {searching ? "Searching ClinicalTrials.gov…" : submitLabel}
      </Button>
    </form>
  )
}
