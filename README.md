# Investment Readiness and Recommendation System

**Live app: https://investment-readiness.streamlit.app/**

Only about **3% of Kenyan adults invest** in formal products such as shares, bonds, Treasury bills or money market funds. This project uses the **2024 FinAccess Household Survey** to help two groups:

- **Individuals:** see the saving and investment options that people like them use, with plain product details and a "what if" comparison. No score about the person.
- **Institutions (SACCOs, banks, fund managers, fintechs):** upload a customer list and get each person's **investor likelihood** (High / Medium / Low), the main reasons, and a ranked list to download.

*Moringa School Data Science, Module 6 capstone, by team **Predictive Minds**.*

## Data
- **2024 FinAccess Household Survey** (Central Bank of Kenya, KNBS and FSD Kenya): 20,870 adults aged 16+ after cleaning.
- **Target:** does the person currently invest (2.7% yes).
- **11 inputs:** questions anyone can answer: age, urban/rural, county, education, marital status, household size, type of work, monthly income, has an ID, uses mobile money, and a 3-question money quiz.
- **Sex is not an input**, so no one's result depends on their sex. It is kept aside only to check fairness.

## Approach
1. **Classifier (for institutions):** compared logistic regression, Random Forest and XGBoost with 5-fold cross-validation on **PR-AUC** (the right score when the "yes" group is rare). Final model: **tuned XGBoost**, calibrated so its probabilities match reality.
2. **Explanations:** SHAP shows how each answer pushed a person's likelihood up or down.
3. **Recommender (for individuals):** finds the 50 most similar people in the survey and suggests the options they use most, plus an investment "next step" that similar people use more than average.

## Key results (test set, people the model never saw)
| | Result |
|---|---|
| PR-AUC | **0.233**, about 8.6 times better than random guessing (0.027) |
| ROC-AUC | **0.870** |
| High band (top ~10% of people) | holds **53%** of investors; 14.3% of them invest (5.3× the average) |
| Fairness | finds the same share of investors among women and men (53% each) |
| Strongest factors | income, education, county, age and type of work |
| Recommender | suggests shares/bonds to 57% of their holders and pension to 84% of pension users |

## Repo layout
```
index.ipynb                         the full analysis notebook (CRISP-DM)
app/app.py                          Streamlit entry point
app/views/                          pages: home, individuals, institutions, about
app/investor_app.py                 engine: cleaning, upload checks, likelihood + reasons, recommender
app/common.py                       shared: cached model, feedback box, standard text
models/investor_app_bundle.joblib   saved models (notebook section 9.1)
data/sample_customers.csv           sample customer list for "Try with sample data"
requirements.txt                    pinned library versions
```

## Run the app locally
```
pip install -r requirements.txt
streamlit run app/app.py
```
Use **Python 3.13** with the pinned versions (scikit-learn 1.6.1, xgboost 3.4.1, pandas 2.2.3, numpy 2.4.6), the same ones the model was trained with.

## Limits
- Investor likelihood shows how closely someone resembles **today's** investors. It is **not** a measure of whether they are able or ready to invest.
- The model finds links in the data, not causes. Survey answers are self-reported and from one year (2024).
- It works less well for young people (16–34), and it is weak at telling who uses a SACCO.
- Women are shown investment suggestions less often, because the people most similar to them invest less today (Kenya's gender gap).
- Product details are general. **For learning only, not financial advice.**

## Team
1. Nickson Kipruto
2. Martin Ngemu
3. Peter Kyalo
4. Mary Nyang'au
5. Cyrus Kirui (team leader) and
6. Fascos Jepleting (scrum)
