"""About and limits: the data, how results are made, fairness, limits and the team (trust)."""
import streamlit as st

from common import DATA_NOTE, DISCLAIMER, feedback_box

st.title("About this app")

st.subheader("The data")
st.write(DATA_NOTE + " Only 2.7% of adults in the survey invest in formal products such as shares, bonds, "
         "Treasury bills or money market funds. The survey was collected in 2024.")

st.subheader("For institutions: investor likelihood")
st.markdown(
    "- A **calibrated XGBoost model** uses the 11 questions to estimate how closely a person resembles "
    "people who already invest. Calibrated means a 10% likelihood really means about 10 in 100 such people invest.\n"
    "- On people it had never seen, the model was about **8.6 times** better than random guessing at finding "
    "investors (PR-AUC 0.233).\n"
    "- **Bands:** High (8% or more), Medium (3% to 8%), Low (below 3%). On our test data, 14.3% of High, 5.0% of "
    "Medium and 0.8% of Low people actually invested.\n"
    "- **Reasons** come from SHAP, which shows how much each answer pushed the likelihood up or down. "
    "Income, education, county, age and type of work matter most."
)

st.subheader("For individuals: options from similar people")
st.markdown(
    "- We find the **50 people in the survey whose answers are most like yours** and show the two options they "
    "use most, plus an investment \"next step\" that people like you use more than average.\n"
    "- If few similar people invest, we suggest starter options (savings, chama or SACCO) first.\n"
    "- Individuals never see a score about themselves."
)

st.subheader("Fairness")
st.markdown(
    "- **Sex is never used**, so no one gets a lower likelihood or different suggestions because of their sex.\n"
    "- The model finds the same share of investors among women and men (53% each at our cut-off).\n"
    "- Women still get investment suggestions less often, because the people most similar to them invest less "
    "today. This reflects Kenya's gender gap in investing (2.0% of women vs 4.4% of men)."
)

st.subheader("Limits")
st.markdown(
    "- Investor likelihood shows how much someone looks like **today's** investors. It is not a measure of "
    "whether they are able or ready to invest.\n"
    "- The model finds links in the data, not causes. Survey answers are self-reported and from one year (2024).\n"
    "- It works less well for young people (16–34) and is weak at telling who uses a SACCO.\n"
    "- Product details are general. Check current terms with a licensed provider.\n"
    "- Results depend on honest, accurate answers."
)

st.subheader("The team")
st.write("Predictive Minds, Moringa School Data Science (Module 6 capstone): Nickson Kipruto, Martin Ngemu, "
         "Peter Kyalo, Mary Nyang'au, Cyrus Kirui and Fascos Jepleting. Technical mentor: Sam Karu.")

st.caption(DISCLAIMER)
feedback_box("about")
