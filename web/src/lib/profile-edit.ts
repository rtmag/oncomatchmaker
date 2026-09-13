import type { MolecularProfile } from "./types"

/** String-typed form state for the clinician-reviewed context fields. */
export interface ContextDraft {
  diagnosis: string
  city: string
  country: string
  latitude: string
  longitude: string
  age: string
  ecog: string
  stage: string
  msi: string
  therapyStatus: "unknown" | "none" | "entered"
  therapies: string
}

export type DraftErrors = Partial<Record<keyof ContextDraft, string>>

const asText = (value: string | number | null) => (value === null ? "" : String(value))
const parseNumber = (value: string) => (value.trim() === "" ? null : Number(value))
const orNull = (value: string) => value.trim() || null

export function draftFromProfile(profile: MolecularProfile): ContextDraft {
  const { disease, patient_context: context } = profile
  return {
    diagnosis: disease.normalized || disease.raw_text,
    city: asText(context.location.city),
    country: asText(context.location.country),
    latitude: asText(context.location.latitude),
    longitude: asText(context.location.longitude),
    age: asText(context.age),
    ecog: asText(context.ecog),
    stage: disease.stage ?? "",
    msi: profile.biomarkers.msi.status ?? "",
    therapyStatus: context.prior_therapies.length ? "entered" : context.prior_therapies_known ? "none" : "unknown",
    therapies: context.prior_therapies.join(", "),
  }
}

function checkRange(value: string, label: string, min: number, max: number, integer = false): string | undefined {
  const parsed = parseNumber(value)
  if (parsed === null) return undefined
  if (!Number.isFinite(parsed) || (integer && !Number.isInteger(parsed))) {
    return `${label} must be ${integer ? "a whole number" : "a number"}.`
  }
  if (parsed < min || parsed > max) return `${label} must be between ${min} and ${max}.`
  return undefined
}

/** Mirrors the pydantic constraints so errors surface before a round trip. */
export function validateDraft(draft: ContextDraft): DraftErrors {
  const errors: DraftErrors = {
    diagnosis: draft.diagnosis.trim() ? undefined : "A confirmed diagnosis is required to search.",
    city: undefined,
    therapies: draft.therapyStatus === "entered" && !draft.therapies.trim() ? "Enter treatments or choose None / Unknown." : undefined,
    country: undefined,
    latitude: checkRange(draft.latitude, "Latitude", -90, 90),
    longitude: checkRange(draft.longitude, "Longitude", -180, 180),
    age: checkRange(draft.age, "Age", 0, 120, true),
  }
  const hasLatitude = draft.latitude.trim() !== ""
  const hasLongitude = draft.longitude.trim() !== ""
  if (!errors.latitude && !errors.longitude && hasLatitude !== hasLongitude) {
    errors.longitude = "Supply both latitude and longitude, or neither."
  }
  return Object.fromEntries(Object.entries(errors).filter(([, message]) => message)) as DraftErrors
}

export function applyDraft(profile: MolecularProfile, draft: ContextDraft): MolecularProfile {
  const changedDiagnosis = draft.diagnosis.trim() !== (profile.disease.normalized || profile.disease.raw_text)
  const sameLocation = draft.city.trim() === (profile.patient_context.location.city ?? "") && draft.country.trim() === (profile.patient_context.location.country ?? "")
  const next: MolecularProfile = {
    ...profile,
    disease: { ...profile.disease, normalized: draft.diagnosis.trim(), stage: orNull(draft.stage), ...(changedDiagnosis ? { ontology_id: null, synonyms: [], normalization_status: "clinician_entered" } : {}) },
    biomarkers: { ...profile.biomarkers, msi: { status: orNull(draft.msi) } },
    patient_context: {
      ...profile.patient_context,
      age: parseNumber(draft.age),
      ecog: draft.ecog === "" ? null : Number(draft.ecog),
      prior_therapies_known: draft.therapyStatus !== "unknown",
      prior_therapies: draft.therapyStatus !== "entered" ? [] : draft.therapies
        .split(",")
        .map((therapy) => therapy.trim())
        .filter(Boolean),
      location: {
        city: orNull(draft.city),
        country: orNull(draft.country),
        latitude: sameLocation ? profile.patient_context.location.latitude : null,
        longitude: sameLocation ? profile.patient_context.location.longitude : null,
      },
    },
  }
  const before = draftFromProfile(profile)
  const changes = Object.keys(before).filter(key => before[key as keyof ContextDraft] !== draft[key as keyof ContextDraft])
  if (changes.length) next.ingestion_provenance = { ...profile.ingestion_provenance, clinician_context: [...((profile.ingestion_provenance?.clinician_context as unknown[]) ?? []), { origin: "user_confirmed_profile", timestamp: new Date().toISOString(), fields: changes, before, after: draft }] }
  return next
}
