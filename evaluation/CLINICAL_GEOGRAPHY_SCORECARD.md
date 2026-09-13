# Independent clinical-match and geographic-access scorecard

Geography is not part of the clinical-trial composite score. The two values are
calculated independently and later displayed as orthogonal axes:

```text
geographic access (y)
100 ┌───────────────────────┬────────────────────────┐
    │ lower match           │ high match             │
    │ high access           │ high access            │
 50 ├───────────────────────┼────────────────────────┤
    │ lower match           │ high match             │
    │ low access            │ low access             │
  0 └───────────────────────┴────────────────────────┘
    0                      70                      100
                  clinical composite (x)
```

The upper-right quadrant highlights trials that combine strong clinical/molecular
fit with an accessible, explicitly recruiting site. A nearby trial cannot improve
its clinical score, and a strong molecular trial cannot improve its geographic
score.

## Clinical composite

The clinical score contains only:

- molecular fit,
- disease fit,
- mechanistic and resistance fit,
- evidence strength,
- eligibility compatibility,
- trial-design relevance.

Each component is 0–100 or `null`, with status, confidence, rationale, missing
information, and evidence references. Explicit molecular, disease, or eligibility
conflicts make the trial unrankable before plotting.

`observed_score` summarizes the known components. `coverage` describes the share
of configured weight supported by known information. The conservative
`composite_score` used for ranking and plotting is:

```text
observed_score × coverage
```

Unknown values remain `null` in component charts rather than appearing as false
zeroes. Trials below the minimum evidence-coverage threshold are not plotted.

## Geographic access

The initial POC geography score uses only Haversine distance to the nearest site
where both the study and individual site are explicitly `RECRUITING`:

```text
100 × exp(-distance_km / 250)
```

No open site, an unknown site status, or an unknown distance produces a `null`
geography score, not zero. Such trials remain visible in a separate “access
unresolved” list and cannot be placed misleadingly on the 2D chart.

The provisional 70/50 quadrant thresholds organize POC review only. They are
configurable and are not validated clinical cutoffs. Future versions may add
travel time and cross-border burden as transparent geographic subcomponents
without changing the clinical score.

## Visualization contract

- X-axis: conservative clinical composite score.
- Y-axis: independent geographic-access score.
- Point label: NCT identifier and short trial title.
- Point color: direct, mechanistic, exploratory, or eligibility-review tier.
- Point size: evidence confidence or evidence coverage.
- Tooltip/report detail: all component scores, unknowns, nearest site, distance,
  registry dates, expert rationales, and source links.
- Unplottable trials: shown beside the chart with the exact missing or conflicting
  reason.
