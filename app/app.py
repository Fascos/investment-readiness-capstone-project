"""Investment Readiness and Recommendation System - Streamlit app.

Two views:
- For individuals: suggested options from similar people (no score about the person)
- For institutions: investor likelihood band (High / Medium / Low) and the main reasons

Run locally:  streamlit run app/app.py
"""
import streamlit as st

from investor_app import AVERAGE_RATE, investor_likelihood, load_bundle, recommend

DISCLAIMER = "For learning only, not personal financial advice. Confirm product terms and licensing with the provider before acting."

st.set_page_config(page_title="Investment Readiness", page_icon="📈", layout="centered")


@st.cache_resource
def get_bundle():
    # Load the saved models once and reuse them for every visitor
    return load_bundle()


bundle = get_bundle()
choices = bundle["form_choices"]

st.title("Investment Readiness and Recommendation System")
st.caption("Built on the 2024 FinAccess Household Survey (CBK, KNBS, FSD Kenya) · Predictive Minds, Moringa School")

# ---------------------------------------------------------------------------
# The form: the 11 questions (sex is not asked)
# ---------------------------------------------------------------------------
with st.form("answers"):
    st.subheader("About you")
    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input("Age", min_value=16, max_value=105, value=30, step=1)
        county = st.selectbox("County", choices["county"])
        urban_rural = st.selectbox("Do you live in an urban or rural area?", choices["urban_rural"])
        household_size = st.number_input("How many people live in your household?", min_value=1, max_value=20, value=4, step=1)
        marital_status = st.selectbox("Marital status", choices["marital_status"])
    with col2:
        education = st.selectbox("Highest level of education", choices["education"])
        livelihood = st.selectbox("Main source of income / type of work", choices["livelihood"])
        prefer_not = st.checkbox("I prefer not to say my income")
        income = st.number_input("Monthly income (KSh)", min_value=0, max_value=10_000_000, value=15_000, step=1_000,
                                 disabled=prefer_not)
        has_id = st.selectbox("Do you have a national ID or passport?", choices["has_id"],
                              format_func=lambda label: label.split("(")[0].strip())
        mobile_money = st.selectbox("Do you use mobile money?", choices["mobile_money"])

    st.subheader("Three quick money questions")
    q1 = st.radio("1. You put KSh 100 in a savings account that pays 10% interest a year. "
                  "After one year, with no withdrawals, how much is in the account?",
                  ["Less than KSh 110", "Exactly KSh 110", "More than KSh 110", "I don't know"], index=None)
    q2 = st.radio("2. Prices go up by 10% this year, and your savings earn 5% interest. "
                  "After one year, can your savings buy more, the same, or less than today?",
                  ["More", "The same", "Less", "I don't know"], index=None)
    q3 = st.radio("3. Which is usually safer?",
                  ["Putting all your money in one investment", "Spreading your money across several investments",
                   "I don't know"], index=None)

    submitted = st.form_submit_button("See my results", type="primary")

if not submitted:
    st.info("Fill in the form and press **See my results**.")
    st.stop()

literacy_score = sum([
    q1 == "Exactly KSh 110",
    q2 == "Less",
    q3 == "Spreading your money across several investments",
])

answers = {
    "age": age,
    "urban_rural": urban_rural,
    "county": county,
    "education": education,
    "marital_status": marital_status,
    "household_size": household_size,
    "livelihood": livelihood,
    "monthly_income": None if prefer_not else income,
    "has_id": has_id,
    "mobile_money": mobile_money,
    "literacy_score": literacy_score,
}

tab_individual, tab_institution = st.tabs(["For individuals", "For institutions"])

# ---------------------------------------------------------------------------
# Individual view: suggestions only, no score about the person
# ---------------------------------------------------------------------------
with tab_individual:
    result = recommend(bundle, answers)
    st.subheader("Options that people like you use")
    if result["starter_step"]:
        st.write("Few people with answers like yours use investment products yet, so here are good places to start.")
    for _, suggestion in result["suggestions"].iterrows():
        with st.container(border=True):
            st.markdown(f"**{suggestion['display_name']}**")
            st.write(suggestion["plain_sentence"])
            with st.expander("Product details"):
                st.markdown(
                    f"- **Risk:** {suggestion['risk']}\n"
                    f"- **Typical minimum:** {suggestion['typical_minimum']}\n"
                    f"- **Getting your money out:** {suggestion['access']}\n"
                    f"- **Time horizon:** {suggestion['time_horizon']}\n"
                    f"- **Regulator:** {suggestion['regulator']}"
                )
    st.caption(f"You answered {literacy_score} of 3 money questions correctly.")
    st.caption(DISCLAIMER)

# ---------------------------------------------------------------------------
# Institution view: likelihood band and reasons
# ---------------------------------------------------------------------------
with tab_institution:
    scored = investor_likelihood(bundle, answers)
    band_meaning = {
        "High": "About 3 times the average chance or more. A good person to approach first.",
        "Medium": "Around or a little above the average chance.",
        "Low": "Below the average chance.",
    }
    st.subheader("Investor likelihood")
    st.metric("Band", scored["band"])
    st.write(band_meaning[scored["band"]])
    st.write(
        f"Likelihood: **{scored['likelihood']:.1%}**, about **{scored['times_average']:.1f} times** "
        f"the average Kenyan adult ({AVERAGE_RATE:.1%})."
    )
    st.markdown("**Main reasons**")
    for sentence in scored["reasons"]:
        st.write(f"- {sentence}")
    st.caption(
        "Investor likelihood shows how closely this person resembles people who already invest. "
        "It is not a measure of whether they are able or ready to invest. Sex is never used to calculate it."
    )
    st.caption(DISCLAIMER)
