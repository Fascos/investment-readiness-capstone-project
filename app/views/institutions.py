"""
For institutions:
upload a customer list or try the sample, then receive
likelihood bands, reasons, charts and a downloadable list.
"""

import logging

import altair as alt
import pandas as pd
import streamlit as st

from common import (
    DATA_NOTE,
    DISCLAIMER,
    feedback_box,
    get_bundle
)
from investor_app import (
    AVERAGE_RATE,
    MAX_UPLOAD_ROWS,
    SAMPLE_PATH,
    likelihood_band,
    prepare_rows,
    score_customers,
    template_columns,
    template_csv,
    validate_upload
)

from llm_layer import (
    build_institution_prompt,
    build_followup_prompt,
    generate_explanation
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Load the deployment bundle
# ------------------------------------------------------------------

bundle = get_bundle()
choices = bundle["form_choices"]


BAND_ORDER = [
    "High",
    "Medium",
    "Low"
]


BAND_MEANING = {
    "High": (
        "8% or more: about 3 times the average or more. "
        "Approach these people first."
    ),
    "Medium": (
        "3% to 8%: around or a little above the average."
    ),
    "Low": (
        "Below 3%: below the average."
    ),
}


# ------------------------------------------------------------------
# CSV reader
# ------------------------------------------------------------------

def read_customer_csv(source):
    """
    Read a customer CSV without interpreting the answer 'None'
    as a missing value.

    Only genuinely empty CSV cells are treated as missing.
    """
    return pd.read_csv(
        source,
        keep_default_na=False,
        na_values=[""]
    )


# ------------------------------------------------------------------
# Page introduction
# ------------------------------------------------------------------

st.title(
    "Find customers who are likely to invest"
)

st.write(
    "**How to use:** upload your customer list as a CSV "
    "file, or press **Try with sample data**. You get each "
    "person's investor likelihood (High, Medium or Low), the "
    "main reasons, and a list to download."
)

st.info(
    "For privacy, do not upload names, national ID numbers, "
    "account numbers, phone numbers, email addresses or other "
    "unnecessary personal information. Use a non-identifying "
    "customer reference in the customer ID column."
)


# ------------------------------------------------------------------
# Required-file structure
# ------------------------------------------------------------------

with st.expander(
    "Which columns does my file need?"
):

    try:
        st.dataframe(
            template_columns(bundle),
            hide_index=True,
            use_container_width=True
        )

        st.download_button(
            "Download an example file",
            template_csv(bundle),
            "customer_list_template.csv",
            "text/csv"
        )

    except Exception:
        logger.exception(
            "Customer upload template could not be prepared"
        )

        st.error(
            "The customer-file template could not be prepared. "
            "Please try again later."
        )


# ------------------------------------------------------------------
# File selection
# ------------------------------------------------------------------

up_col, sample_col = st.columns(
    [3, 1]
)

uploaded = up_col.file_uploader(
    "Upload your customer list (CSV)",
    type="csv"
)


if sample_col.button(
    "Try with sample data",
    use_container_width=True
):

    try:
        st.session_state["inst_raw"] = (
            read_customer_csv(
                SAMPLE_PATH
            )
        )

        st.session_state["inst_source"] = (
            "sample data "
            "(people from the survey's test set)"
        )

    except FileNotFoundError:
        logger.exception(
            "Institution sample CSV file was not found"
        )

        st.error(
            "The sample file is missing. "
            "Please upload your own list for now."
        )

    except Exception:
        logger.exception(
            "Institution sample CSV could not be loaded"
        )

        st.error(
            "The sample data could not be loaded. "
            "Please upload your own customer file."
        )


if uploaded is not None:

    try:
        st.session_state["inst_raw"] = (
            read_customer_csv(
                uploaded
            )
        )

        st.session_state["inst_source"] = (
            uploaded.name
        )

    except Exception:
        logger.exception(
            "Uploaded institution CSV could not be read | "
            "filename=%s",
            getattr(
                uploaded,
                "name",
                "unknown"
            )
        )

        st.error(
            "We couldn't read that file. Please upload a "
            "comma-separated CSV file with a header row, "
            "like the example file above."
        )

        st.stop()


# ------------------------------------------------------------------
# Wait for an uploaded or sample file
# ------------------------------------------------------------------

if "inst_raw" not in st.session_state:

    st.info(
        "Upload a customer list or try the sample data "
        "to get started."
    )

    feedback_box("institutions")
    st.stop()


raw = st.session_state["inst_raw"]


# ------------------------------------------------------------------
# File-size validation
# ------------------------------------------------------------------

if len(raw) > MAX_UPLOAD_ROWS:

    st.error(
        f"The file has {len(raw):,} rows. "
        f"Please upload at most "
        f"{MAX_UPLOAD_ROWS:,} rows at a time."
    )

    st.stop()


# ------------------------------------------------------------------
# Validate uploaded records
# ------------------------------------------------------------------

try:
    valid, problems, missing = (
        validate_upload(
            bundle,
            raw
        )
    )

except Exception:
    logger.exception(
        "Institution upload validation failed | "
        "rows=%s",
        len(raw)
    )

    st.error(
        "We couldn't validate the customer file. "
        "Please compare its columns and answers with "
        "the example template, then try again."
    )

    st.stop()


if missing:

    st.error(
        "Your file is missing these columns: **"
        + ", ".join(missing)
        + "**. Open **Which columns does my file need?** "
        "above for the list and an example file."
    )

    st.stop()


if len(problems):

    st.warning(
        f"{problems['Row in file'].nunique()} row(s) had "
        "answers we couldn't use and were skipped. Fix them "
        "and upload again to include them."
    )

    with st.expander(
        "See the problems"
    ):

        st.dataframe(
            problems,
            hide_index=True,
            use_container_width=True
        )


if valid.empty:

    st.error(
        "No rows could be scored. "
        "Please check the problems above."
    )

    st.stop()


# ------------------------------------------------------------------
# Score valid customers
# ------------------------------------------------------------------

try:
    with st.spinner(
        f"Scoring {len(valid):,} people..."
    ):

        results = score_customers(
            bundle,
            valid
        )

except Exception:
    logger.exception(
        "Institution batch scoring failed | valid_rows=%s",
        len(valid)
    )

    st.error(
        "Sorry, we couldn't score the customer list. "
        "Please check the input data and try again."
    )

    st.stop()


st.caption(
    f"Source: {st.session_state['inst_source']}"
)


# ------------------------------------------------------------------
# Headline metrics
# ------------------------------------------------------------------

counts = (
    results["band"]
    .value_counts()
    .reindex(
        BAND_ORDER,
        fill_value=0
    )
)


m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "People scored",
    f"{len(results):,}"
)

m2.metric(
    "High",
    f"{counts['High']:,}"
)

m3.metric(
    "Medium",
    f"{counts['Medium']:,}"
)

m4.metric(
    "Low",
    f"{counts['Low']:,}"
)


# ------------------------------------------------------------------
# Band explanation
# ------------------------------------------------------------------

with st.expander(
    "What do the bands mean?"
):

    for band in BAND_ORDER:

        st.markdown(
            f"- **{band}:** "
            f"{BAND_MEANING[band]}"
        )

    st.caption(
        "The average Kenyan adult in the survey has a "
        f"{AVERAGE_RATE:.1%} chance of being an investor. "
        "On our test data, 14.3% of High, 5.0% of Medium "
        "and 0.8% of Low people actually invested."
    )


# ------------------------------------------------------------------
# Band-distribution chart
# ------------------------------------------------------------------

st.subheader(
    "People by band"
)

try:
    band_chart = (
        alt.Chart(
            counts
            .rename_axis("Band")
            .reset_index(name="People")
        )
        .mark_bar(
            color="#4C72B0"
        )
        .encode(
            x=alt.X(
                "Band:N",
                sort=BAND_ORDER,
                title=None
            ),
            y=alt.Y(
                "People:Q"
            ),
            tooltip=[
                "Band",
                "People"
            ]
        )
    )

    st.altair_chart(
        band_chart,
        use_container_width=True
    )

except Exception:
    logger.exception(
        "Institution band chart failed to render"
    )

    st.warning(
        "The results were calculated, but the band chart "
        "could not be displayed."
    )


# ------------------------------------------------------------------
# Ranked customer list
# ------------------------------------------------------------------

st.subheader(
    "Ranked list"
)

show_bands = st.multiselect(
    "Show bands",
    BAND_ORDER,
    default=BAND_ORDER
)


table = (
    results[
        results["band"].isin(
            show_bands
        )
    ]
    .rename(columns={
        "customer_id": "Customer",
        "band": "Band",
        "likelihood_pct": "Likelihood (%)",
        "times_average": "Times the average",
        "reason_1": "Main reason",
        "reason_2": "Second reason",
        "reason_3": "Third reason",
        "sex": "Sex",
    })
)


st.dataframe(
    table,
    hide_index=True,
    use_container_width=True
)


try:
    download_csv = results.to_csv(
        index=False
    )

    st.download_button(
        "Download the ranked list (CSV)",
        download_csv,
        "investor_likelihood_ranked.csv",
        "text/csv",
        type="primary"
    )

except Exception:
    logger.exception(
        "Institution ranked-list download failed"
    )

    st.warning(
        "The results are available on screen, but the "
        "download file could not be prepared."
    )


# ------------------------------------------------------------------
# Report by sex
# ------------------------------------------------------------------

if "sex" in results.columns:

    st.subheader(
        "Report by sex"
    )

    try:
        by_sex = (
            results
            .groupby("sex")["band"]
            .value_counts(
                normalize=True
            )
            .mul(100)
            .round(1)
            .unstack(
                fill_value=0
            )
            .reindex(
                columns=BAND_ORDER,
                fill_value=0
            )
        )

        by_sex.insert(
            0,
            "People",
            results["sex"].value_counts()
        )

        st.dataframe(
            by_sex.rename(
                columns=lambda column: (
                    f"{column} (%)"
                    if column in BAND_ORDER
                    else column
                )
            ),
            use_container_width=True
        )

        st.caption(
            "Sex is never used to calculate the likelihood. "
            "It is shown only so you can report on your "
            "customers and check that groups are reached fairly."
        )

    except Exception:
        logger.exception(
            "Institution sex-group report failed"
        )

        st.warning(
            "Customer scores were calculated, but the report "
            "by sex could not be displayed."
        )


# ------------------------------------------------------------------
# Individual customer view
# ------------------------------------------------------------------

st.subheader(
    "Look at one person"
)

person_id = st.selectbox(
    "Choose a person",
    results[
        "customer_id"
    ].astype(str).tolist()
)


row_index = results.index[
    results[
        "customer_id"
    ].astype(str) == person_id
][0]


person = results.loc[
    row_index
]


answers = valid.loc[
    row_index
].to_dict()


d1, d2 = st.columns(2)

d1.metric(
    "Band",
    person["band"]
)

d2.metric(
    "Likelihood",
    f"{person['likelihood_pct']:.1f}%",
    help=(
        f"About "
        f"{person['times_average']:.1f}× "
        "the average"
    )
)


for k in (
    1,
    2,
    3
):

    if person[f"reason_{k}"]:

        st.write(
            f"- {person[f'reason_{k}']}"
        )
        
top_reasons = [
    person[f"reason_{k}"]
    for k in (1, 2, 3)
    if pd.notna(person[f"reason_{k}"])
    and str(person[f"reason_{k}"]).strip()
]
# ------------------------------------------------------------------
# Gemini explanation of the institutional result
# ------------------------------------------------------------------
if st.button("Explain this result"):

    try:
        with st.spinner("Preparing your explanation..."):

            prompt = build_institution_prompt(
                person["band"],
                top_reasons
            )

            explanation = generate_explanation(prompt)

        st.subheader("Understanding this result")
        st.write(explanation)

    except Exception:
        logger.exception("Institution Gemini explanation failed")
        st.warning(
            "Our explanation service is temporarily overloaded. "
            "Please try again in a short while."
        )
        
# ------------------------------------------------------------------
# Ask a follow-up question
# ------------------------------------------------------------------

st.subheader("Ask a follow-up question")

followup_question = st.text_input(
    "What would you like to understand about this result?",
    placeholder="e.g. What does a High likelihood band mean?"
)

if st.button("Ask Gemini"):

    if followup_question.strip():

        try:
            with st.spinner("Preparing your answer..."):

                context = {
                    "likelihood_band": person["band"],
                    "top_reasons": top_reasons
                }

                prompt = build_followup_prompt(
                    followup_question,
                    context
                )

                answer = generate_explanation(prompt)

            st.write(answer)

        except Exception:
            logger.exception("Institution follow-up question failed")
            st.warning(
                "Our explanation service is temporarily overloaded. "
                "Please try again in a short while."
            )

    else:
        st.warning("Please enter a question first.")
# ------------------------------------------------------------------
# Institutional what-if analysis
# ------------------------------------------------------------------

with st.expander(
    "What if this person's situation changed?"
):

    st.caption(
        "What-if results show how the model output changes "
        "when an input changes. They do not prove that changing "
        "the input will cause a person to invest."
    )

    w1, w2 = st.columns(2)

    what_if = dict(answers)

    what_if["education"] = w1.selectbox(
        "Education",
        choices["education"],
        index=choices["education"].index(
            answers["education"]
        ),
        key="inst_wi_edu"
    )

    income_missing = pd.isna(
        answers["monthly_income"]
    )

    base_income = (
        0
        if income_missing
        else int(
            answers["monthly_income"]
        )
    )

    new_income = w2.number_input(
        "Monthly income (KSh)",
        min_value=0,
        max_value=10_000_000,
        value=base_income,
        step=5_000,
        key="inst_wi_income",
        help=(
            "Income was not given for this person"
            if income_missing
            else None
        )
    )

    # Preserve a missing income unless a value has
    # actually been entered in the what-if analysis.
    what_if["monthly_income"] = (
        None
        if income_missing and new_income == 0
        else new_income
    )

    try:
        prepared_what_if = prepare_rows(
            bundle,
            pd.DataFrame(
                [what_if]
            )
        )

        new_prob = (
            bundle["final_model"]
            .predict_proba(
                prepared_what_if
            )[:, 1][0]
        )

        change = (
            new_prob * 100
            - person["likelihood_pct"]
        )

        st.metric(
            "Likelihood with these changes",
            f"{new_prob:.1%}",
            f"{change:+.1f} points"
        )

        st.write(
            "Band: **"
            + likelihood_band(
                new_prob,
                bundle["settings"]
            )
            + "** "
            f"(now: {person['band']})"
        )

    except Exception:
        logger.exception(
            "Institution individual what-if scoring failed | "
            "customer_reference=%s",
            person_id
        )

        st.error(
            "We couldn't complete this what-if comparison. "
            "Please review the changed values and try again."
        )


# ------------------------------------------------------------------
# Notes and feedback
# ------------------------------------------------------------------

st.caption(
    "Investor likelihood shows how closely a person resembles "
    "people who already invest. It is not a measure of whether "
    "they are able or ready to invest."
)

st.caption(DATA_NOTE)
st.caption(DISCLAIMER)
feedback_box("institutions")
