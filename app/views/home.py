"""Home page: what the app does, for whom, and where to start (understandable in 10 seconds)."""
import streamlit as st

from common import DATA_NOTE, DISCLAIMER

st.title("Investment Readiness and Recommendation System")
st.markdown(
    "**Helping Kenyan adults find a good next step with their money, and helping SACCOs, banks and "
    "fund managers find people who are likely to invest.**"
)

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.markdown("#### 🙋 For individuals")
        st.write("Answer 11 short questions and 3 money questions. See the saving and investment options "
                 "that people like you use, with plain details on each.")
        st.page_link("views/individuals.py", label="Find my options", icon="➡️")
with col2:
    with st.container(border=True):
        st.markdown("#### 🏦 For institutions")
        st.write("Upload a customer list (or try our sample). Get each person's investor likelihood "
                 "(High, Medium or Low), the main reasons, and a list to download.")
        st.page_link("views/institutions.py", label="Score a customer list", icon="➡️")

st.markdown("#### How it works")
st.markdown(
    "1. **Similar people:** we compare your answers with thousands of Kenyans in a national survey.\n"
    "2. **Investor likelihood (institutions only):** a model trained on that survey estimates how closely "
    "a person resembles people who already invest. It is not a judgement of whether someone is ready.\n"
    "3. **Explained results:** every result comes with its main reasons in plain words."
)
st.page_link("views/about.py", label="Read about the data, method and limits", icon="ℹ️")

st.caption(DATA_NOTE)
st.caption(DISCLAIMER)
