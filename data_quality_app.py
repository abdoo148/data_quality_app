import streamlit as st
import pandas as pd
import plotly.express as px
import uuid
import re
from fpdf import FPDF

# ==========================================
# PDF GENERATION (FIXED + OPTIMIZED)
# ==========================================
def create_pdf(quality_score, error_summary, total_rows, rules_applied, df_profile):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 10, "Data Quality Report", ln=1, align='C')
    pdf.ln(5)

    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f"Total Rows: {total_rows}", ln=1)
    pdf.cell(0, 8, f"Quality Score: {quality_score:.1f}%", ln=1)
    pdf.ln(5)

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, "Rules Applied:", ln=1)
    pdf.set_font('Arial', '', 10)
    for r in rules_applied:
        pdf.cell(0, 6, f"- {r}", ln=1)

    pdf.ln(5)

    if not error_summary.empty:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, "Errors:", ln=1)

        pdf.set_font('Arial', '', 10)
        for _, row in error_summary.iterrows():
            pdf.cell(0, 6, f"{row['نوع الخطأ']} - {row['عدد السجلات المتأثرة']}", ln=1)

    # ✅ FIX
    return pdf.output(dest='S').encode('latin-1')


# ==========================================
# CACHE (PERFORMANCE BOOST)
# ==========================================
@st.cache_data
def load_data(file, sheet):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    return pd.read_excel(file, sheet_name=sheet)


@st.cache_data
def generate_pdf_cached(score, err_summary, total, rules, profile):
    return create_pdf(score, err_summary, total, rules, profile)


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def suggest_primary_key(df):
    keywords = ['id', 'code', 'no', 'number', 'key', 'رقم', 'كود']
    for col in df.columns:
        if any(k in col.lower() for k in keywords):
            if df[col].nunique() == len(df):
                return col
    return None


def run_checks(df, primary_key, mandatory_cols, v_cols, pattern, rules):
    errors = {}
    applied = []

    # Primary key
    if primary_key:
        applied.append(f"PK: {primary_key}")
        dup = df[df.duplicated(subset=[primary_key], keep=False)]
        if not dup.empty:
            errors['تكرار'] = dup

    # Mandatory
    if mandatory_cols:
        applied.append("Mandatory fields")
        miss = df[df[mandatory_cols].isnull().any(axis=1)]
        if not miss.empty:
            errors['مفقودة'] = miss

    # Pattern
    if v_cols:
        applied.append("Pattern check")
        for col in v_cols:
            bad = df[~df[col].astype(str).str.match(pattern, na=False) & df[col].notnull()]
            if not bad.empty:
                errors[f'صيغة ({col})'] = bad

    return errors, applied


# ==========================================
# UI
# ==========================================
st.set_page_config(layout="wide")
st.title("🚀 Data Quality Smart Checker")

uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx'])

if uploaded_file:
    sheet = None
    if uploaded_file.name.endswith('.xlsx'):
        xls = pd.ExcelFile(uploaded_file)
        sheet = st.selectbox("Sheet", xls.sheet_names)

    df = load_data(uploaded_file, sheet)

    st.success("File loaded successfully")

    st.write(df.head())

    # CONFIG
    pk = suggest_primary_key(df)
    primary_key = st.selectbox("Primary Key", ["None"] + list(df.columns), index=0 if not pk else list(df.columns).index(pk)+1)

    mandatory = st.multiselect("Mandatory Columns", df.columns)

    v_cols = st.multiselect("Pattern Columns", df.columns)
    pattern = r'^\d+$'

    if st.button("Run Analysis"):
        with st.spinner("Analyzing..."):

            errors, rules = run_checks(
                df,
                None if primary_key == "None" else primary_key,
                mandatory,
                v_cols,
                pattern,
                []
            )

            if not errors:
                st.success("Perfect Data ✅")
            else:
                total = len(df)
                total_bad = sum(len(v) for v in errors.values())

                score = max(0, 100 - (total_bad / total * 100))

                st.metric("Quality Score", f"{score:.1f}%")

                err_summary = pd.DataFrame({
                    'نوع الخطأ': list(errors.keys()),
                    'عدد السجلات المتأثرة': [len(v) for v in errors.values()]
                })

                st.plotly_chart(px.bar(err_summary, x='نوع الخطأ', y='عدد السجلات المتأثرة'))

                # PDF
                with st.spinner("Generating PDF..."):
                    pdf_bytes = generate_pdf_cached(score, err_summary, total, rules, df.describe())

                if pdf_bytes:
                    st.download_button(
                        "Download PDF",
                        data=pdf_bytes,
                        file_name="report.pdf",
                        mime="application/pdf"
                    )

                # Details
                for k, v in errors.items():
                    with st.expander(k):
                        st.dataframe(v)
                        st.download_button(
                            f"Download {k}",
                            v.to_csv(index=False).encode(),
                            f"{k}.csv"
                        )
