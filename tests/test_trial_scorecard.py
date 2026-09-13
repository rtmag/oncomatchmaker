"""Clinical matching and geographic access must remain separate score axes."""

import unittest

from schemas.trial_scorecard import CLINICAL_DIMENSIONS, DimensionScore
from trials.scorecard import (
    clinical_trial_score,
    geographic_access_score,
    trial_plot_position,
)


def dimensions(value=80, status="supported"):
    return [
        DimensionScore(name, value, status, 0.8, rationale=("Synthetic test",))
        for name in CLINICAL_DIMENSIONS
    ]


class TrialScorecardTests(unittest.TestCase):
    def test_geography_cannot_change_clinical_composite(self):
        clinical = clinical_trial_score(dimensions())
        nearby = geographic_access_score(
            5, study_status="RECRUITING", site_status="RECRUITING"
        )
        distant = geographic_access_score(
            3000, study_status="RECRUITING", site_status="RECRUITING"
        )
        self.assertEqual(clinical.composite_score, 80)
        self.assertGreater(nearby.score, distant.score)
        self.assertEqual(clinical.composite_score, 80)

    def test_unknown_is_null_and_reported_through_coverage(self):
        scores = dimensions()
        scores[-1] = DimensionScore(
            "trial_design_relevance",
            None,
            "unknown",
            None,
            missing_information=("Trial design review",),
        )
        clinical = clinical_trial_score(scores)
        self.assertEqual(clinical.observed_score, 80)
        self.assertEqual(clinical.coverage, 0.95)
        self.assertEqual(clinical.composite_score, 76)

    def test_clinical_conflict_makes_trial_unrankable(self):
        scores = dimensions()
        scores[0] = DimensionScore(
            "molecular_fit",
            None,
            "conflict",
            0.99,
            rationale=("Trial excludes the reported alteration",),
        )
        clinical = clinical_trial_score(scores)
        self.assertFalse(clinical.rankable)
        self.assertIsNone(clinical.composite_score)

    def test_closed_or_unconfirmed_site_has_no_geography_score(self):
        closed = geographic_access_score(
            5, study_status="RECRUITING", site_status="ACTIVE_NOT_RECRUITING"
        )
        upcoming = geographic_access_score(
            5, study_status="NOT_YET_RECRUITING", site_status="NOT_YET_RECRUITING"
        )
        self.assertIsNone(closed.score)
        self.assertIsNone(upcoming.score)
        with self.assertRaises(ValueError):
            geographic_access_score(
                -1, study_status="RECRUITING", site_status="ACTIVE_NOT_RECRUITING"
            )

    def test_best_quadrant_requires_both_independent_axes(self):
        clinical = clinical_trial_score(dimensions(90))
        accessible = geographic_access_score(
            10, study_status="RECRUITING", site_status="RECRUITING"
        )
        difficult = geographic_access_score(
            1000, study_status="RECRUITING", site_status="RECRUITING"
        )
        self.assertEqual(
            trial_plot_position(clinical, accessible).quadrant,
            "high_match_high_access",
        )
        self.assertEqual(
            trial_plot_position(clinical, difficult).quadrant,
            "high_match_low_access",
        )

    def test_unresolved_geography_is_not_plotted_as_zero(self):
        clinical = clinical_trial_score(dimensions(90))
        unknown = geographic_access_score(
            None, study_status="RECRUITING", site_status="RECRUITING"
        )
        position = trial_plot_position(clinical, unknown)
        self.assertEqual(position.plot_status, "not_plottable")
        self.assertIsNone(position.geography_y)


if __name__ == "__main__":
    unittest.main()
