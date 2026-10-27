import csv, json, streamlit as st
st.title("SOAR Decisions")
exps = {e["decision_id"]: e for e in map(json.loads, open("out/explanations.jsonl"))}
rows = list(csv.DictReader(open("out/pipeline_log.csv")))[::-1]
for d in rows[:50]:
    e = exps.get(d["decision_id"])
    if not e: continue
    st.subheader(f"{d['chosen_action'].upper()}  ({float(d['confidence_score']):.0%})")
    st.write(e["plain_language_summary"])
    st.caption(f"Origin: {e['decision_origin']} | Pattern: {e['matched_pattern_or_rule']}")
    st.bar_chart(e["factor_weights"])