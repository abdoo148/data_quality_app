import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import uuid
import re
import io
from fpdf import FPDF

# ==========================================
# 0. دوال مساعدة (توليد PDF والتعرف الذكي)
# ==========================================
def create_pdf(quality_score, error_summary, total_rows):
    """إنشاء ملف PDF مع رسومات بيانية باستخدام Matplotlib (الحل الجذري للمشاكل)"""
    pdf = FPDF()
    pdf.add_page()
    
    # تصميم الهيدر (Header)
    pdf.set_fill_color(118, 75, 162) 
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 20, txt="Data Quality Report", ln=1, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    
    # 1. الملخص التنفيذي
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, txt="1. Executive Summary", ln=1, align='L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, txt=f"Total Records Analyzed: {total_rows}", ln=1)
    pdf.cell(0, 8, txt=f"Overall Quality Score: {quality_score:.1f}%", ln=1)
    
    # رسم شريط تقدم بصري بسيط (بدون مكتبات)
    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(10, pdf.get_y(), 100, 5)
    if quality_score > 80: pdf.set_fill_color(0, 200, 0) 
    elif quality_score > 50: pdf.set_fill_color(255, 165, 0)
    else: pdf.set_fill_color(220, 20, 60)
    pdf.rect(10, pdf.get_y(), max(0.1, quality_score), 5, 'F')
    pdf.ln(15)
    
    # 2. قسم الرسومات البيانية (استخدام Matplotlib كحل جذري)
    if not error_summary.empty:
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, txt="2. Visual Error Distribution", ln=1, align='L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # إنشاء الرسم البياني باستخدام Matplotlib (مستقر جداً)
        plt.figure(figsize=(10, 5))
        # ترجمة مبسطة للأسماء في الرسم
        translated_labels = []
        for label in error_summary['نوع الخطأ']:
            if 'تكرار' in label: translated_labels.append('Duplicates')
            elif 'مفقودة' in label: translated_labels.append('Missing')
            elif 'صيغة' in label: translated_labels.append('Format')
            elif 'تناقض' in label: translated_labels.append('Conflict')
            else: translated_labels.append('Other')

        plt.bar(translated_labels, error_summary['عدد السجلات المتأثرة'], color='#764ba2')
        plt.title('Error Count by Category')
        plt.ylabel('Number of Records')
        
        # حفظ الرسم في ذاكرة مؤقتة كصورة
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', bbox_inches='tight')
        plt.close() # إغلاق الشكل لتوفير الذاكرة
        
        pdf.image(img_buf, x=15, y=None, w=180)
        pdf.ln(10)

    # 3. جدول التفاصيل
    if not error_summary.empty:
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, txt="3. Detailed Error Summary", ln=1, align='L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(130, 10, txt='Error Category', border=1, align='C', fill=True)
        pdf.cell(60, 10, txt='Count', border=1, ln=1, align='C', fill=True)
        
        pdf.set_font('Arial', '', 11)
        for _, row in error_summary.iterrows():
            pdf.cell(130, 10, txt=str(row['نوع الخطأ'])[:65], border=1)
            pdf.cell(60, 10, txt=str(row['عدد السجلات المتأثرة']), border=1, ln=1, align='C')

    return pdf.output()

def suggest_primary_key(df):
    """اقتراح ذكي للمعرف الفريد"""
    keywords = ['id', 'code', 'no', 'number', 'key', 'رقم', 'كود', 'معرف']
    for col in df.columns:
        if any(kw in str(col).lower() for kw in keywords) and df[col].nunique() == len(df):
            return col
    return "بدون تحديد"

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(page_title="المُقيّم الذكي V4", page_icon="🚀", layout="wide")

if 'dynamic_rules' not in st.session_state: st.session_state.dynamic_rules = []
if 'compare_rules' not in st.session_state: st.session_state.compare_rules = []

def add_rule(): st.session_state.dynamic_rules.append({"id": str(uuid.uuid4())})
def remove_rule(rid): st.session_state.dynamic_rules = [r for r in st.session_state.dynamic_rules if r['id'] != rid]
def add_compare_rule(): st.session_state.compare_rules.append({"id": str(uuid.uuid4())})
def remove_compare_rule(rid): st.session_state.compare_rules = [r for r in st.session_state.compare_rules if r['id'] != rid]

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    * { font-family: 'Tajawal', sans-serif; }
    body { direction: RTL; text-align: right; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; }
    .rule-container { border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px; margin-bottom: 10px; background-color: #f8f9fa; border-right: 5px solid #764ba2; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. القائمة الجانبية
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2875/2875071.png", width=80)
    st.title("إعدادات البيانات")
    uploaded_file = st.file_uploader("📁 ارفع ملفك (CSV/Excel)", type=['csv', 'xlsx'])
    
    selected_sheet = None
    if uploaded_file and uploaded_file.name.endswith(('.xlsx', '.xls')):
        xls = pd.ExcelFile(uploaded_file)
        selected_sheet = st.selectbox("📑 اختر ورقة العمل:", xls.sheet_names)

    if st.button("🗑️ مسح كل القواعد"):
        st.session_state.dynamic_rules = []
        st.session_state.compare_rules = []
        st.rerun()

# ==========================================
# 3. الواجهة الرئيسية
# ==========================================
if uploaded_file is None:
    st.info("يرجى رفع ملف بيانات للبدء 👈")
else:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, sheet_name=selected_sheet)
    columns = df.columns.tolist()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 1. التحليل الإحصائي", "🛡️ 2. القواعد والصيغ", "🔗 3. المنطق المترابط", "🎯 4. لوحة النتائج"])

    with tab1:
        st.header("الفحص الإحصائي")
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي السجلات", f"{len(df):,}")
        c2.metric("إجمالي الأعمدة", len(columns))
        c3.metric("القيم المفقودة", f"{df.isnull().sum().sum():,}")
        st.dataframe(df.head(10), use_container_width=True)

    with tab2:
        st.header("معايير الجودة الأساسية")
        col_a, col_b = st.columns(2)
        with col_a:
            pk_idx = (columns.index(suggest_primary_key(df)) + 1) if suggest_primary_key(df) in columns else 0
            primary_key = st.selectbox("🔑 المعرف الفريد (ID):", ["بدون تحديد"] + columns, index=pk_idx)
        with col_b:
            mandatory_cols = st.multiselect("📝 الأعمدة الإلزامية:", columns, default=columns)

        st.markdown("---")
        st.subheader("🛠️ التحقق من الأنماط (Pattern Validation)")
        regex_patterns = {
            "بريد إلكتروني (Email)": r'^[\w\.-]+@[\w\.-]+\.\w+$',
            "أرقام فقط (Digits)": r'^\d+$',
            "تاريخ (YYYY-MM-DD)": r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$',
            "تاريخ (DD/MM/YYYY)": r'^(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/\d{4}$'
        }
        c_r1, c_r2 = st.columns(2)
        v_cols = c_r1.multiselect("اختر الأعمدة للفحص:", columns)
        v_pattern = c_r2.selectbox("الصيغة المطلوبة:", list(regex_patterns.keys()))

    with tab3:
        st.header("المحرك المنطقي المتقدم")
        st.button("➕ إضافة قاعدة مقارنة", on_click=add_compare_rule)
        for r in st.session_state.compare_rules:
            rid = r['id']
            with st.container(border=True):
                cl1, cl2, cl3, cl4 = st.columns([3, 2, 3, 1])
                cl1.selectbox("العمود 1:", columns, key=f"c1_{rid}")
                cl2.selectbox("يجب أن يكون:", [">", "<", "==", "!="], key=f"op_{rid}")
                cl3.selectbox("مقارنة بـ 2:", columns, key=f"c2_{rid}")
                cl4.button("🗑️", key=f"del_c_{rid}", on_click=remove_compare_rule, args=(rid,))

        st.markdown("---")
        st.button("➕ إضافة قاعدة شرطية", on_click=add_rule)
        for r in st.session_state.dynamic_rules:
            rid = r['id']
            with st.container(border=True):
                r1_c1, r1_c2, r1_c3, r1_c4 = st.columns([3, 2, 3, 1])
                c_col = r1_c1.selectbox("إذا كان العمود:", columns, key=f"cond_col_{rid}")
                c_type = r1_c2.selectbox("الحالة:", ["يساوي قيمة", "فارغ (Empty)", "ليس فارغاً (Not Empty)"], key=f"cond_type_{rid}")
                if st.session_state[f"cond_type_{rid}"] == "يساوي قيمة":
                    u_vals = df[c_col].dropna().unique().tolist() if c_col else []
                    r1_c3.selectbox("القيمة:", u_vals, key=f"cond_val_{rid}")
                else: r1_c3.info("فحص حالة العمود")
                r1_c4.button("🗑️", key=f"del_r_{rid}", on_click=remove_rule, args=(rid,))
                r2_c1, r2_c2 = st.columns(2)
                r2_c1.selectbox("فإن العمود النتيجة:", columns, key=f"target_col_{rid}")
                r2_c2.selectbox("يجب أن يكون:", ["ليس فارغاً", "فارغاً"], key=f"target_type_{rid}")

    with tab4:
        st.header("🎯 النتائج")
        if st.button("🚀 بدء التحليل", use_container_width=True, type="primary"):
            total = len(df)
            errs = {}
            # التحليل
            if primary_key != "بدون تحديد":
                dups = df[df.duplicated(subset=[primary_key], keep=False)]
                if not dups.empty: errs['تكرار في المعرف الفريد'] = dups
            if mandatory_cols:
                miss = df[df[mandatory_cols].isnull().any(axis=1)]
                if not miss.empty: errs['بيانات إلزامية مفقودة'] = miss
            if v_cols:
                pat = regex_patterns[v_pattern]
                for col in v_cols:
                    bad = df[~df[col].astype(str).str.match(pat, na=False) & df[col].notnull()]
                    if not bad.empty: errs[f'صيغة خاطئة في ({col})'] = bad
            for r in st.session_state.dynamic_rules:
                rid = r['id']
                # ... منطق الفحص الشرطي ...
                c_col, c_type = st.session_state[f"cond_col_{rid}"], st.session_state[f"cond_type_{rid}"]
                t_col, t_type = st.session_state[f"target_col_{rid}"], st.session_state[f"target_type_{rid}"]
                if c_type == "يساوي قيمة": c_mask = (df[c_col] == st.session_state[f"cond_val_{rid}"])
                elif c_type == "فارغ (Empty)": c_mask = df[c_col].isnull()
                else: c_mask = df[c_col].notnull()
                t_err = df[t_col].isnull() if t_type == "ليس فارغاً" else df[t_col].notnull()
                bad = df[c_mask & t_err]
                if not bad.empty: errs[f'مخالفة شرط: {c_col}'] = bad

            if not errs: st.success("🎉 البيانات ممتازة!")
            else:
                score = max(0, 100 - (sum(len(v) for v in errs.values()) / (total * max(1, len(errs))) * 100))
                st.markdown(f'<div class="metric-card"><h3>الجودة</h3><h1>{score:.1f}%</h1></div>', unsafe_allow_html=True)
                err_summary = pd.DataFrame({'نوع الخطأ': list(errs.keys()), 'عدد السجلات المتأثرة': [len(v) for v in errs.values()]})
                st.plotly_chart(px.bar(err_summary, x='نوع الخطأ', y='عدد السجلات المتأثرة'), use_container_width=True)
                
                # تحميل PDF (الحل المستقر)
                pdf_bytes = create_pdf(score, err_summary, total)
                st.download_button("📥 تحميل التقرير (PDF)", data=pdf_bytes, file_name="DQ_Report.pdf", mime="application/pdf")
                for k, v in errs.items():
                    with st.expander(f"🔴 {k} ({len(v)})"): st.dataframe(v)
