import json, streamlit as st
st.title("SOAR Decisions")
rows = [json.loads(l) for l in open("pipeline_log.jsonl")][::-1]
for r in rows[:50]:
    d, e = r["decision"], r["explanation"]
    st.subheader(f"{d['chosen_action'].upper()}  ({d['confidence_score']:.0%})")
    st.write(e["plain_language_summary"])
    st.caption(f"Origin: {e['decision_origin']} | Pattern: {e['matched_pattern_or_rule']}")
    st.bar_chart(e["factor_weights"])