import streamlit as st
import pandas as pd
import plotly.express as px
import uuid
import re
import io
from fpdf import FPDF

# ==========================================
# 0. دوال مساعدة (توليد PDF نصي احترافي)
# ==========================================
def create_pdf(quality_score, error_summary, total_rows, rules_applied):
    """إنشاء ملف PDF نصي يحتوي على جداول وإحصائيات بدون رسومات (لضمان الاستقرار)"""
    pdf = FPDF()
    pdf.add_page()
    
    # Header - الهيدر
    pdf.set_fill_color(118, 75, 162) 
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 20, txt="Data Quality Final Report", ln=1, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    
    # 1. Executive Summary - الملخص التنفيذي
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, txt="1. Executive Summary", ln=1, align='L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, txt=f"Total Records Analyzed: {total_rows}", ln=1)
    pdf.cell(0, 8, txt=f"Overall Quality Score: {quality_score:.1f}%", ln=1)
    pdf.cell(0, 8, txt=f"Status: {'Excellent' if quality_score > 90 else 'Action Required'}", ln=1)
    pdf.ln(10)
    
    # 2. Applied Rules - القواعد التي تم تطبيقها
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, txt="2. Assessment Rules Applied", ln=1, align='L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    for rule in rules_applied:
        pdf.multi_cell(0, 8, txt=f"- {rule}")
    pdf.ln(5)

    # 3. Detailed Error Table - جدول الأخطاء التفصيلي
    if not error_summary.empty:
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, txt="3. Detected Issues Statistics", ln=1, align='L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Header الجدول
        pdf.set_font('Arial', 'B', 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(140, 10, txt='Issue Category', border=1, align='C', fill=True)
        pdf.cell(50, 10, txt='Affected Rows', border=1, ln=1, align='C', fill=True)
        
        # محتوى الجدول
        pdf.set_font('Arial', '', 11)
        for _, row in error_summary.iterrows():
            err_txt = str(row['نوع الخطأ'])
            # ترجمة بسيطة للتقرير
            if 'تكرار' in err_txt: err_txt = "Duplicated ID/Key"
            elif 'مفقودة' in err_txt: err_txt = "Null/Missing Values"
            elif 'صيغة' in err_txt: err_txt = "Pattern Mismatch"
            elif 'مخالفة' in err_txt: err_txt = "Logic Rule Violation"
            
            pdf.cell(140, 10, txt=err_txt[:70], border=1)
            pdf.cell(50, 10, txt=str(row['عدد السجلات المتأثرة']), border=1, ln=1, align='C')
    else:
        pdf.set_font('Arial', 'I', 12)
        pdf.cell(0, 10, txt="No data quality issues were detected based on the current rules.", ln=1)

    return pdf.output()

def suggest_primary_key(df):
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

def add_rule(): st.session_state.dynamic_rules.append({"id": str(uuid.uuid4())})
def remove_rule(rid): st.session_state.dynamic_rules = [r for r in st.session_state.dynamic_rules if r['id'] != rid]

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
            pk_sugg = suggest_primary_key(df)
            pk_idx = (columns.index(pk_sugg) + 1) if pk_sugg in columns else 0
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
        v_cols = c_r1.multiselect("اختر العمود/الأعمدة للفحص:", columns, key="pattern_cols")
        v_pattern = c_r2.selectbox("الصيغة المطلوبة:", list(regex_patterns.keys()))

    with tab3:
        st.header("المحرك المنطقي المتقدم")
        st.write("يمكنك الآن بناء شروط تعتمد على (القيمة، الفراغ، أو الامتلاء).")
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
                r2_c2.selectbox("يجب أن يكون:", ["ليس فارغاً (Not Empty)", "فارغاً (Empty)"], key=f"target_type_{rid}")

    with tab4:
        st.header("🎯 النتائج والتقرير")
        if st.button("🚀 تشغيل محرك التحليل الشامل", use_container_width=True, type="primary"):
            total = len(df)
            errs = {}
            applied_rules_list = []
            
            with st.spinner('جاري التحليل...'):
                # 1. فحص التفرد
                if primary_key != "بدون تحديد":
                    applied_rules_list.append(f"Unique Key Check on: {primary_key}")
                    dups = df[df.duplicated(subset=[primary_key], keep=False)]
                    if not dups.empty: errs['تكرار في المعرف الفريد'] = dups
                
                # 2. فحص الاكتمال
                if mandatory_cols:
                    applied_rules_list.append(f"Completeness Check on: {', '.join(mandatory_cols)}")
                    miss = df[df[mandatory_cols].isnull().any(axis=1)]
                    if not miss.empty: errs['بيانات إلزامية مفقودة'] = miss
                
                # 3. فحص الأنماط
                if v_cols:
                    applied_rules_list.append(f"Pattern Validation ({v_pattern}) on: {', '.join(v_cols)}")
                    pat = regex_patterns[v_pattern]
                    for col in v_cols:
                        bad = df[~df[col].astype(str).str.match(pat, na=False) & df[col].notnull()]
                        if not bad.empty: errs[f'صيغة خاطئة في ({col})'] = bad
                
                # 4. فحص المنطق الشرطي
                for r in st.session_state.dynamic_rules:
                    rid = r['id']
                    c_col, c_type = st.session_state[f"cond_col_{rid}"], st.session_state[f"cond_type_{rid}"]
                    t_col, t_type = st.session_state[f"target_col_{rid}"], st.session_state[f"target_type_{rid}"]
                    
                    applied_rules_list.append(f"Conditional: If {c_col} is {c_type} then {t_col} must be {t_type}")
                    
                    if c_type == "يساوي قيمة": c_mask = (df[c_col] == st.session_state[f"cond_val_{rid}"])
                    elif c_type == "فارغ (Empty)": c_mask = df[c_col].isnull()
                    else: c_mask = df[c_col].notnull()
                    
                    t_err = df[t_col].isnull() if t_type == "ليس فارغاً (Not Empty)" else df[t_col].notnull()
                    bad = df[c_mask & t_err]
                    if not bad.empty: errs[f'مخالفة شرط: {c_col} -> {t_col}'] = bad

            if not errs:
                st.success("🎉 البيانات مطابقة بنسبة 100% لجميع القواعد!")
            else:
                total_bad = sum(len(v) for v in errs.values())
                score = max(0, 100 - (total_bad / (total * max(1, len(errs))) * 100))
                st.markdown(f'<div class="metric-card"><h3>مؤشر جودة البيانات</h3><h1>{score:.1f}%</h1></div>', unsafe_allow_html=True)
                
                err_summary = pd.DataFrame({'نوع الخطأ': list(errs.keys()), 'عدد السجلات المتأثرة': [len(v) for v in errs.values()]})
                st.plotly_chart(px.bar(err_summary, x='نوع الخطأ', y='عدد السجلات المتأثرة', title="توزيع المشاكل المكتشفة"), use_container_width=True)

                st.subheader("🖨️ طباعة التقرير النصي")
                pdf_bytes = create_pdf(score, err_summary, total, applied_rules_list)
                st.download_button("📥 تحميل التقرير النصي (PDF)", data=pdf_bytes, file_name="Data_Quality_Report.pdf", mime="application/pdf", use_container_width=True)

                for k, v in errs.items():
                    with st.expander(f"🔴 {k} ({len(v)} سجل)"):
                        st.dataframe(v, use_container_width=True)
                        st.download_button(f"تحميل CSV لـ {k}", v.to_csv(index=False).encode('utf-8-sig'), f"{k}.csv", "text/csv")
