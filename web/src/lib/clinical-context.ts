import type { MolecularProfile } from './types'

export interface OptionalClinicalContext {
  msi: string
  ecog: string
  stage: string
  therapyStatus: 'unknown' | 'none' | 'entered'
  therapies: string
}
export const EMPTY_CLINICAL_CONTEXT: OptionalClinicalContext = { msi: '', ecog: '', stage: '', therapyStatus: 'unknown', therapies: '' }

/** Blank intake fields preserve reported values; explicit entries are auditable overrides. */
export function applyIntakeContext(profile: MolecularProfile, context: OptionalClinicalContext): MolecularProfile {
  const updated = structuredClone(profile)
  const changes: { field: string; before: unknown; after: unknown }[] = []
  const record = (field: string, before: unknown, after: unknown) => { if (JSON.stringify(before) !== JSON.stringify(after)) changes.push({ field, before, after }) }
  if (context.msi) { record('msi', profile.biomarkers.msi.status, context.msi); updated.biomarkers.msi.status = context.msi }
  if (context.ecog !== '') { const ecog = Number(context.ecog); if (!Number.isInteger(ecog) || ecog < 0 || ecog > 5) throw new Error('ECOG must be 0–5 or unknown.'); record('ecog', profile.patient_context.ecog, ecog); updated.patient_context.ecog = ecog }
  if (context.stage.trim()) { record('stage', profile.disease.stage, context.stage.trim()); updated.disease.stage = context.stage.trim() }
  if (context.therapyStatus !== 'unknown') {
    const therapies = context.therapyStatus === 'none' ? [] : context.therapies.split(',').map(s => s.trim()).filter(Boolean)
    if (context.therapyStatus === 'entered' && !therapies.length) throw new Error('Enter prior treatments or choose Unknown / None.')
    record('prior_therapies', { values: profile.patient_context.prior_therapies, known: profile.patient_context.prior_therapies_known }, { values: therapies, known: true })
    updated.patient_context.prior_therapies = therapies; updated.patient_context.prior_therapies_known = true
  }
  if (changes.length) updated.ingestion_provenance = { ...profile.ingestion_provenance, clinician_context: [...((profile.ingestion_provenance?.clinician_context as unknown[]) ?? []), { origin: 'user_entered_at_intake', timestamp: new Date().toISOString(), changes }] }
  return updated
}
