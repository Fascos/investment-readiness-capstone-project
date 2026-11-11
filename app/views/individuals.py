"""For individuals: answer the questions, see options that people like you use, and try "what if"."""
import streamlit as st

from common import DATA_NOTE, DISCLAIMER, feedback_box, get_bundle
from investor_app import EXAMPLE_PEOPLE, recommend, standardise_answer

bundle = get_bundle()
choices = bundle["form_choices"]

# The 3 money questions (same topics as the survey: interest, inflation, spreading risk)
QUIZ = {
    "ind_q1": ("1. You put KSh 100 in a savings account that pays 10% interest a year. "
               "After one year, with no withdrawals, how much is in the account?",
               ["Less than KSh 110", "Exactly KSh 110", "More than KSh 110", "I don't know"], "Exactly KSh 110"),
    "ind_q2": ("2. Prices go up by 10% this year, and your savings earn 5% interest. "
               "After one year, can your savings buy more, the same, or less than today?",
               ["More", "The same", "Less", "I don't know"], "Less"),
    "ind_q3": ("3. Which is usually safer?",
               ["Putting all your money in one investment", "Spreading your money across several investments",
                "I don't know"], "Spreading your money across several investments"),
}
FORM_FIELDS = ["urban_rural", "county", "education", "marital_status", "livelihood", "has_id", "mobile_money"]

# Sensible starting answers (choices the person must make are left empty)
st.session_state.setdefault("ind_age", 30)
st.session_state.setdefault("ind_household_size", 4)
st.session_state.setdefault("ind_income", 15_000)
st.session_state.setdefault("ind_prefer_not", False)
st.session_state.setdefault("ind_has_id", standardise_answer(bundle, "has_id", "Yes"))
st.session_state.setdefault("ind_mobile_money", "Yes")


def load_example(name):
    # Fill the form with one of the example people
    person = EXAMPLE_PEOPLE[name]
    st.session_state["ind_age"] = person["age"]
    st.session_state["ind_household_size"] = person["household_size"]
    st.session_state["ind_income"] = person["monthly_income"]
    st.session_state["ind_prefer_not"] = False
    for field in FORM_FIELDS:
        st.session_state[f"ind_{field}"] = standardise_answer(bundle, field, person[field])
    for k, key in enumerate(QUIZ):
        _, options, correct = QUIZ[key]
        st.session_state[key] = correct if k < person["literacy_score"] else "I don't know"
    st.session_state.pop("answers", None)


st.title("Find options that suit people like you")
st.write("Answer the questions below and press **See my options**. We compare your answers with thousands of "
         "Kenyans in a national survey and show the saving and investment options that people like you use. "
         "We never give you a score.")

st.markdown("**Or try an example:**")
example_cols = st.columns(len(EXAMPLE_PEOPLE))
for col, name in zip(example_cols, EXAMPLE_PEOPLE):
    col.button(name, on_click=load_example, args=(name,), use_container_width=True)

with st.form("individual_form"):
    st.subheader("About you")
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Age", min_value=16, max_value=105, step=1, key="ind_age")
        st.selectbox("County", choices["county"], index=None, placeholder="Choose your county", key="ind_county")
        st.selectbox("Do you live in an urban or rural area?", choices["urban_rural"], index=None,
                     placeholder="Choose one", key="ind_urban_rural")
        st.number_input("How many people live in your household?", min_value=1, max_value=20, step=1,
                        key="ind_household_size")
        st.selectbox("Marital status", choices["marital_status"], index=None, placeholder="Choose one",
                     key="ind_marital_status")
    with col2:
        st.selectbox("Highest level of education", choices["education"], index=None, placeholder="Choose one",
                     key="ind_education")
        st.selectbox("Main source of income / type of work", choices["livelihood"], index=None,
                     placeholder="Choose one", key="ind_livelihood")
        st.number_input("Monthly income (KSh)", min_value=0, max_value=10_000_000, step=1_000, key="ind_income")
        st.checkbox("I prefer not to say my income", key="ind_prefer_not")
        st.selectbox("Do you have a national ID or passport?", choices["has_id"], key="ind_has_id",
                     format_func=lambda label: "Yes" if label.lower().startswith("has id") else "No")
        st.selectbox("Do you use mobile money?", choices["mobile_money"], key="ind_mobile_money")

    st.subheader("Three quick money questions")
    for key, (question, options, _) in QUIZ.items():
        st.radio(question, options, index=None, key=key)

    submitted = st.form_submit_button("See my options", type="primary")

if submitted:
    missing = [label for field, label in [("county", "county"), ("urban_rural", "urban or rural"),
                                          ("marital_status", "marital status"), ("education", "education"),
                                          ("livelihood", "type of work")]
               if st.session_state.get(f"ind_{field}") is None]
    if missing:
        st.warning("Please answer: " + ", ".join(missing) + ".")
        st.stop()
    st.session_state["answers"] = {
        "age": st.session_state["ind_age"],
        "urban_rural": st.session_state["ind_urban_rural"],
        "county": st.session_state["ind_county"],
        "education": st.session_state["ind_education"],
        "marital_status": st.session_state["ind_marital_status"],
        "household_size": st.session_state["ind_household_size"],
        "livelihood": st.session_state["ind_livelihood"],
        "monthly_income": None if st.session_state["ind_prefer_not"] else st.session_state["ind_income"],
        "has_id": st.session_state["ind_has_id"],
        "mobile_money": st.session_state["ind_mobile_money"],
        "literacy_score": sum(st.session_state.get(key) == correct for key, (_, _, correct) in QUIZ.items()),
    }

if "answers" not in st.session_state:
    st.info("Fill in the form, or try an example, to see your options.")
    feedback_box("individuals")
    st.stop()

answers = st.session_state["answers"]


def show_suggestions(result, compact=False):
    # One card per suggestion: name, plain sentence and product details
    for _, suggestion in result["suggestions"].iterrows():
        with st.container(border=True):
            st.markdown(f"**{suggestion['display_name']}**")
            st.write(suggestion["plain_sentence"])
            if not compact:
                with st.expander("Product details"):
                    st.markdown(
                        f"- **Risk:** {suggestion['risk']}\n"
                        f"- **Typical minimum:** {suggestion['typical_minimum']}\n"
                        f"- **Getting your money out:** {suggestion['access']}\n"
                        f"- **Time horizon:** {suggestion['time_horizon']}\n"
                        f"- **Regulator:** {suggestion['regulator']}"
                    )


try:
    with st.spinner("Finding people like you..."):
        result = recommend(bundle, answers)
except Exception:
    st.error("Sorry, something went wrong while finding your options. Please check your answers and try again.")
    st.stop()

st.subheader("Options that people like you use")
if result["starter_step"]:
    st.write("Few people with answers like yours use investment products yet, so here are good places to start.")
show_suggestions(result)
st.caption(f"You answered {answers['literacy_score']} of 3 money questions correctly.")

# What if: change a few answers and compare the options side by side
st.subheader("What if...?")
st.write("Change an answer to see how the options for people like you would change.")
wcol1, wcol2, wcol3 = st.columns(3)
what_if = dict(answers)
what_if["education"] = wcol1.selectbox("Education", choices["education"],
                                       index=choices["education"].index(answers["education"]), key="wi_education")
current_income = answers["monthly_income"] if answers["monthly_income"] is not None else 15_000
what_if["monthly_income"] = wcol2.number_input("Monthly income (KSh)", min_value=0, max_value=10_000_000,
                                               value=int(current_income), step=5_000, key="wi_income")
what_if["literacy_score"] = wcol3.slider("Money questions correct", 0, 3, int(answers["literacy_score"]),
                                         key="wi_literacy")

if what_if == answers:
    st.caption("Change one of the answers above to compare.")
else:
    what_if_result = recommend(bundle, what_if)
    now_col, then_col = st.columns(2)
    with now_col:
        st.markdown("**Your options now**")
        show_suggestions(result, compact=True)
    with then_col:
        st.markdown("**What if**")
        show_suggestions(what_if_result, compact=True)
    new_options = set(what_if_result["suggestions"]["display_name"]) - set(result["suggestions"]["display_name"])
    if new_options:
        st.success("New option(s) that would appear: " + ", ".join(sorted(new_options)) + ".")
    else:
        st.info("The same options would be suggested.")

st.caption(DATA_NOTE)
st.caption(DISCLAIMER)
feedback_box("individuals")
