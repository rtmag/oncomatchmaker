# Geographic access: domestic-access-v1

Geography stays independent of clinical scoring and never establishes eligibility.
Only explicitly RECRUITING sites in RECRUITING studies with coordinates qualify.

This prototype policy scores straight-line distance `d` in kilometres:

- Same country: `100 * exp(-d / 1500)`.
- Different countries: `60 * exp(-d / 1500)`.
- Missing country: original distance-only fallback `100 * exp(-d / 250)`, visibly
  labeled country unknown. No domestic benefit is inferred.

These are explicit product heuristics, not validated estimates of travel burden.
The domestic scale keeps several-hundred-kilometre travel relatively accessible;
the international ceiling represents additional cross-border friction. Long
domestic journeys still lose points. Language, actual transport routes, travel
time, cost, visas, disability and patient preferences are not inferred. Countries
with difficult domestic connections may need different policies in future.
Country comparison uses normalized names and a small explicit alias table; it is
not comprehensive geopolitical or language normalization.

Both all-study landscape and expert-reviewed trials select the highest-scoring
open site using this policy. `accessible_site` records that site and distance;
`nearest_site` remains unchanged for compatibility and literal nearest-distance
sorting. `geography_access` records policy version, travel context and explanation.
Existing cached results retain their original scores; run a new search after
restarting the backend. No clinical score weights or hard-conflict gates change.

Tests cover Daegu/Busan/Changwon to Seoul (domestic scores at least 75), Korean
country-name aliases, same-distance international comparisons, long-distance
decay, unknown countries, closed sites, upcoming-only studies, and identical
landscape/reviewed-site scoring.
