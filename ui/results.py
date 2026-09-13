import streamlit as st


def render_results(results):
    st.subheader("Approved treatment evidence")
    st.caption(
        "US FDA evidence; not an assessment of approval or availability in your country. Full indication requirements remain to be reviewed."
    )
    if not results.approved_options:
        st.info("No association found in this limited curated dataset.")
    for option in results.approved_options:
        with st.expander(
            f"{option.therapy} · {option.context.replace('_', ' ')}", expanded=True
        ):
            st.write(f"{option.biomarker} · {option.disease} · {option.evidence_level}")
            st.write(option.applicability)
            for restriction in option.restrictions:
                st.write(f"• {restriction}")
            for url in option.sources:
                st.link_button("Evidence source", url)
            st.caption(f"Source checked {option.verified_at}")
    st.subheader("Experimental clinical trials")
    st.write(f"Search status: {results.search_status}")
    for warning in results.warnings:
        st.warning(warning)
    if not results.trials and results.search_status == "complete":
        st.info(
            "Search completed with no trial candidates. This does not establish that no suitable trials exist."
        )
    for category, label in [
        ("recruiting", "Recruiting candidates"),
        ("not_yet_recruiting", "Not yet recruiting"),
        ("review", "Compatibility requires review"),
        ("excluded", "Known prescreening mismatch"),
    ]:
        trials = [r for r in results.trials if r.category == category]
        if not trials:
            continue
        st.markdown(f"### {label}")
        for item in trials:
            trial = item.trial
            with st.expander(f"{trial.nct_id} · {trial.title}"):
                st.write(
                    f"{trial.status} · {', '.join(trial.phase) or 'Phase unavailable'}"
                )
                st.write(
                    f"Relevance score: {item.match.overall_score}/100 · component coverage: {item.match.coverage:.0%}"
                )
                st.caption(
                    "Heuristic priority, not a probability of eligibility or benefit. Unknown components earn no points."
                )
                st.json(item.match.components)
                for reason in item.match.rationale:
                    st.write(reason)
                st.write(f"Prescreen: {item.eligibility.status}")
                st.dataframe(
                    [c.model_dump() for c in item.eligibility.criteria],
                    use_container_width=True,
                )
                if item.nearest_site:
                    site = item.nearest_site
                    st.write(
                        f"Nearest explicitly recruiting site: {site.site.name}, {site.site.city}, {site.site.country} · approximately {site.distance_km} km straight-line"
                    )
                else:
                    st.write("Nearest recruiting site/distance unavailable.")
                st.write("Conditions:", trial.conditions)
                st.write("Interventions:", trial.interventions)
                st.text(trial.eligibility_text or "Eligibility text unavailable")
                st.json([s.model_dump() for s in trial.sites], expanded=False)
                for url in trial.sources:
                    st.link_button("View trial source", url)
                st.caption(
                    f"Retrieved {trial.retrieved_at}"
                    + (" · cached response" if trial.cached else " · live response")
                )
    st.download_button(
        "Download results JSON",
        results.model_dump_json(indent=2),
        "match_results.json",
        "application/json",
    )
