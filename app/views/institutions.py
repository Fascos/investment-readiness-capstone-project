"""For institutions: upload a customer list (or try the sample) -> likelihood bands, reasons, charts, download."""
import altair as alt
import pandas as pd
import streamlit as st

from common import DATA_NOTE, DISCLAIMER, feedback_box, get_bundle
from investor_app import (AVERAGE_RATE, MAX_UPLOAD_ROWS, SAMPLE_PATH, likelihood_band, prepare_rows,
                          score_customers, template_columns, template_csv, validate_upload)

bundle = get_bundle()
choices = bundle["form_choices"]
BAND_ORDER = ["High", "Medium", "Low"]
BAND_MEANING = {
    "High": "8% or more: about 3 times the average or more. Approach these people first.",
    "Medium": "3% to 8%: around or a little above the average.",
    "Low": "Below 3%: below the average.",
}

st.title("Find customers who are likely to invest")
st.write("**How to use:** upload your customer list as a CSV file, or press **Try with sample data**. "
         "You get each person's investor likelihood (High, Medium or Low), the main reasons, and a list to download.")

with st.expander("Which columns does my file need?"):
    st.dataframe(template_columns(bundle), hide_index=True, use_container_width=True)
    st.download_button("Download an example file", template_csv(bundle), "customer_list_template.csv", "text/csv")

up_col, sample_col = st.columns([3, 1])
uploaded = up_col.file_uploader("Upload your customer list (CSV)", type="csv")
if sample_col.button("Try with sample data", use_container_width=True):
    try:
        st.session_state["inst_raw"] = pd.read_csv(SAMPLE_PATH)
        st.session_state["inst_source"] = "sample data (people from the survey's test set)"
    except FileNotFoundError:
        st.error("The sample file is missing. Please upload your own list for now.")

if uploaded is not None:
    try:
        st.session_state["inst_raw"] = pd.read_csv(uploaded)
        st.session_state["inst_source"] = uploaded.name
    except Exception:
        st.error("We couldn't read that file. Please upload a comma-separated (CSV) file with a header row, "
                 "like the example file above.")
        st.stop()

if "inst_raw" not in st.session_state:
    st.info("Upload a customer list or try the sample data to get started.")
    feedback_box("institutions")
    st.stop()

raw = st.session_state["inst_raw"]
if len(raw) > MAX_UPLOAD_ROWS:
    st.error(f"The file has {len(raw):,} rows. Please upload at most {MAX_UPLOAD_ROWS:,} rows at a time.")
    st.stop()

valid, problems, missing = validate_upload(bundle, raw)
if missing:
    st.error("Your file is missing these columns: **" + ", ".join(missing) + "**. "
             "Open **Which columns does my file need?** above for the list and an example file.")
    st.stop()
if len(problems):
    st.warning(f"{problems['Row in file'].nunique()} row(s) had answers we couldn't use and were skipped. "
               "Fix them and upload again to include them.")
    with st.expander("See the problems"):
        st.dataframe(problems, hide_index=True, use_container_width=True)
if valid.empty:
    st.error("No rows could be scored. Please check the problems above.")
    st.stop()

try:
    with st.spinner(f"Scoring {len(valid):,} people..."):
        results = score_customers(bundle, valid)
except Exception:
    st.error("Sorry, something went wrong while scoring the list. Please check the file and try again.")
    st.stop()

st.caption(f"Source: {st.session_state['inst_source']}")

# Headline numbers
counts = results["band"].value_counts().reindex(BAND_ORDER, fill_value=0)
m1, m2, m3, m4 = st.columns(4)
m1.metric("People scored", f"{len(results):,}")
m2.metric("High", f"{counts['High']:,}")
m3.metric("Medium", f"{counts['Medium']:,}")
m4.metric("Low", f"{counts['Low']:,}")

with st.expander("What do the bands mean?"):
    for band in BAND_ORDER:
        st.markdown(f"- **{band}:** {BAND_MEANING[band]}")
    st.caption(f"The average Kenyan adult in the survey has a {AVERAGE_RATE:.1%} chance of being an investor. "
               "On our test data, 14.3% of High, 5.0% of Medium and 0.8% of Low people actually invested.")

st.subheader("People by band")
band_chart = (
    alt.Chart(counts.rename_axis("Band").reset_index(name="People"))
    .mark_bar(color="#4C72B0")
    .encode(x=alt.X("Band:N", sort=BAND_ORDER, title=None), y=alt.Y("People:Q"),
            tooltip=["Band", "People"])
)
st.altair_chart(band_chart, use_container_width=True)

# Ranked list
st.subheader("Ranked list")
show_bands = st.multiselect("Show bands", BAND_ORDER, default=BAND_ORDER)
table = results[results["band"].isin(show_bands)].rename(columns={
    "customer_id": "Customer", "band": "Band", "likelihood_pct": "Likelihood (%)",
    "times_average": "Times the average", "reason_1": "Main reason", "reason_2": "Second reason",
    "reason_3": "Third reason", "sex": "Sex",
})
st.dataframe(table, hide_index=True, use_container_width=True)
st.download_button("Download the ranked list (CSV)", results.to_csv(index=False),
                   "investor_likelihood_ranked.csv", "text/csv", type="primary")

# Report by sex (only if the file has a sex column; sex is never used to calculate the likelihood)
if "sex" in results:
    st.subheader("Report by sex")
    by_sex = (results.groupby("sex")["band"].value_counts(normalize=True).mul(100).round(1)
              .unstack(fill_value=0).reindex(columns=BAND_ORDER, fill_value=0))
    by_sex.insert(0, "People", results["sex"].value_counts())
    st.dataframe(by_sex.rename(columns=lambda c: f"{c} (%)" if c in BAND_ORDER else c), use_container_width=True)
    st.caption("Sex is never used to calculate the likelihood. It is shown only so you can report on your "
               "customers and check that groups are reached fairly.")

# One person: details and what if
st.subheader("Look at one person")
person_id = st.selectbox("Choose a person", results["customer_id"].astype(str).tolist())
row_index = results.index[results["customer_id"].astype(str) == person_id][0]
person = results.loc[row_index]
answers = valid.loc[row_index].to_dict()

d1, d2 = st.columns(2)
d1.metric("Band", person["band"])
d2.metric("Likelihood", f"{person['likelihood_pct']:.1f}%", help=f"About {person['times_average']:.1f}× the average")
for k in (1, 2, 3):
    if person[f"reason_{k}"]:
        st.write(f"- {person[f'reason_{k}']}")

with st.expander("What if this person's situation changed?"):
    w1, w2 = st.columns(2)
    what_if = dict(answers)
    what_if["education"] = w1.selectbox("Education", choices["education"],
                                        index=choices["education"].index(answers["education"]), key="inst_wi_edu")
    income_missing = pd.isna(answers["monthly_income"])
    base_income = 0 if income_missing else int(answers["monthly_income"])
    new_income = w2.number_input("Monthly income (KSh)", min_value=0, max_value=10_000_000,
                                 value=base_income, step=5_000, key="inst_wi_income",
                                 help="Income was not given for this person" if income_missing else None)
    # Keep a missing income missing unless the user actually types one
    what_if["monthly_income"] = None if income_missing and new_income == 0 else new_income
    new_prob = bundle["final_model"].predict_proba(prepare_rows(bundle, pd.DataFrame([what_if])))[:, 1][0]
    change = new_prob * 100 - person["likelihood_pct"]
    st.metric("Likelihood with these changes", f"{new_prob:.1%}", f"{change:+.1f} points")
    st.write(f"Band: **{likelihood_band(new_prob, bundle['settings'])}** (now: {person['band']})")

st.caption("Investor likelihood shows how closely a person resembles people who already invest. It is not a "
           "measure of whether they are able or ready to invest.")
st.caption(DATA_NOTE)
st.caption(DISCLAIMER)
feedback_box("institutions")
