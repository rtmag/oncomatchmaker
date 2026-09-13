import { Field, inputClass } from '@/components/ui/field'
import type { OptionalClinicalContext } from '@/lib/clinical-context'

export function OptionalClinicalFields({ value, onChange, disabled }: { value: OptionalClinicalContext; onChange: (value: OptionalClinicalContext) => void; disabled: boolean }) {
  const update = (key: keyof OptionalClinicalContext, text: string) => onChange({ ...value, [key]: text })
  return <details className="rounded-xl border border-border p-4"><summary className="cursor-pointer text-sm font-medium">Optional clinical context · MSI, ECOG, stage, treatments</summary><p className="my-3 text-xs text-muted-foreground">Leave blank if unknown. Reported values will be filled from the PDF; entered values are marked as user-provided and reviewed before Astra runs.</p><fieldset disabled={disabled} className="grid gap-3">
    <Field label="MSI (optional)">{control => <select {...control} className={inputClass} value={value.msi} onChange={e => update('msi', e.target.value)}><option value="">Use report / unknown</option><option value="high">MSI-high</option><option value="stable">Microsatellite stable</option><option value="not_detected">MSI not detected</option><option value="indeterminate">Indeterminate</option></select>}</Field>
    <Field label="ECOG (optional)">{control => <select {...control} className={inputClass} value={value.ecog} onChange={e => update('ecog', e.target.value)}><option value="">Use report / unknown</option>{[0,1,2,3,4,5].map(x => <option key={x}>{x}</option>)}</select>}</Field>
    <Field label="Stage (optional)">{control => <input {...control} className={inputClass} value={value.stage} onChange={e => update('stage', e.target.value)} maxLength={80} placeholder="Unknown" />}</Field>
    <Field label="Prior treatment history (optional)">{control => <select {...control} className={inputClass} value={value.therapyStatus} onChange={e => update('therapyStatus', e.target.value)}><option value="unknown">Use report / unknown</option><option value="none">Confirmed no prior treatments</option><option value="entered">Enter prior treatments</option></select>}</Field>
    {value.therapyStatus === 'entered' && <Field label="Prior treatments" hint="Comma-separated">{control => <input {...control} className={inputClass} value={value.therapies} onChange={e => update('therapies', e.target.value)} maxLength={500} />}</Field>}
  </fieldset></details>
}
