"""
About and limits:
the data, how results are made, fairness, limits and the team.
"""

import streamlit as st

from common import DATA_NOTE, DISCLAIMER, feedback_box


st.title("About this app")


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

st.subheader("The data")

st.write(
    DATA_NOTE
    + " Only 2.7% of adults in the survey invest in formal "
    "products such as shares, bonds, Treasury bills or money "
    "market funds. The survey was collected in 2024."
)


# ------------------------------------------------------------
# Institutional model
# ------------------------------------------------------------

st.subheader("For institutions: investor likelihood")

st.markdown(
    "- A **calibrated XGBoost model** uses the 11 questions to "
    "estimate how closely a person resembles people who already "
    "invest. Calibration aims to align predicted probabilities "
    "with observed rates. For example, among sufficiently similar "
    "cases receiving probabilities around 10%, approximately "
    "10 in 100 would ideally be expected to invest.\n"

    "- On the held-out test set, the model achieved a "
    "**PR-AUC of 0.233**, compared with an approximate no-skill "
    "baseline of **0.027**. This is about **8.6 times the baseline "
    "PR-AUC**.\n"

    "- **Bands:** High (8% or more), Medium (3% to 8%), "
    "Low (below 3%). On the held-out test data, 14.3% of people "
    "in the High band, 5.0% in the Medium band and 0.8% in the "
    "Low band were actual investors.\n"

    "- **Reasons** come from SHAP, which shows how much each "
    "answer pushed the model's investor-likelihood estimate "
    "up or down. Income, education, county, age and type of "
    "work were among the most influential features."
)


# ------------------------------------------------------------
# Individual recommendation system
# ------------------------------------------------------------

st.subheader(
    "For individuals: options from similar people"
)

st.markdown(
    "- We find the **50 people in the survey whose answers are "
    "most similar to yours** and use their reported financial "
    "product use to generate suggestions.\n"

    "- Recommendations are based on what similar people use; "
    "they are not predictions of investment returns or personal "
    "suitability assessments.\n"

    "- If there is limited evidence among similar people, "
    "starter options such as savings, chama or SACCO may be "
    "prioritised.\n"

    "- Individuals never receive an investor-likelihood score "
    "or High, Medium or Low likelihood band."
)


# ------------------------------------------------------------
# Fairness
# ------------------------------------------------------------

st.subheader("Fairness")

st.markdown(
    "- **Sex is not used as an input** to calculate investor "
    "likelihood or find similar people. It is retained only for "
    "fairness evaluation and institutional group reporting.\n"

    "- At the selected model cut-off, the measured investor "
    "recall was approximately 53% for both women and men in "
    "the project's evaluation.\n"

    "- Recommendation outcomes may still differ between groups "
    "because the recommender reflects financial-product-use "
    "patterns observed in the survey. Excluding sex therefore "
    "removes direct use of sex but does not by itself guarantee "
    "identical outcomes between groups."
)


# ------------------------------------------------------------
# Limitations
# ------------------------------------------------------------

st.subheader("Limits")

st.markdown(
    "- Investor likelihood indicates how closely someone "
    "resembles **current investors in the 2024 survey**. "
    "It is not a measure of whether someone is able or ready "
    "to invest.\n"

    "- The model identifies statistical associations in the "
    "survey data, not causal relationships. Changing one input "
    "does not necessarily cause investment behaviour to change.\n"

    "- Survey responses are self-reported and represent a "
    "specific period, so patterns may change over time.\n"

    "- Model performance is weaker for some groups, including "
    "younger adults aged 16–34, and the recommendation system "
    "has limitations for less common financial products.\n"

    "- Product details are general educational information. "
    "Users should confirm current terms, fees, risks and provider "
    "licensing before acting.\n"

    "- Results depend on the quality and accuracy of the "
    "information supplied."
)


# ------------------------------------------------------------
# Team
# ------------------------------------------------------------

st.subheader("The team")

st.write(
    "Predictive Minds, Moringa School Data Science "
    "(Module 6 capstone): Nickson Kipruto, Martin Ngemu, "
    "Peter Kyalo, Mary Nyang'au, Cyrus Kirui and Fascos "
    "Jepleting. Technical mentor: Sam Karu."
)


# ------------------------------------------------------------
# Disclaimer and feedback
# ------------------------------------------------------------

st.caption(DISCLAIMER)
feedback_box("about")