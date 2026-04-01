import streamlit as st
import pandas as pd
import plotly.express as px
import uuid
import re
from fpdf import FPDF

# ==========================================
# 0. دوال مساعدة (توليد PDF باللغة الإنجليزية)
# ==========================================
def create_pdf(quality_score, error_summary, total_rows):
    """إنشاء ملف PDF يحتوي على ملخص الأخطاء بالإنجليزية لتفادي مشاكل الخطوط"""
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, txt="Data Quality Assessment Report", ln=1, align='C')
    pdf.ln(10)
    
    pdf.set_font('Arial', '', 14)
    pdf.cell(0, 10, txt=f"Total Analyzed Records: {total_rows}", ln=1, align='L')
    pdf.cell(0, 10, txt=f"Overall Quality Score: {quality_score:.1f}%", ln=1, align='L')
    pdf.ln(10)
    
    if not error_summary.empty:
        pdf.cell(0, 10, txt="Detected Errors Details:", ln=1, align='L')
        pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(130, 10, txt='Error Type', border=1, align='C', fill=True)
        pdf.cell(60, 10, txt='Affected Records', border=1, ln=1, align='C', fill=True)
        
        pdf.set_font('Arial', '', 12)
        for index, row in error_summary.iterrows():
            err_type = str(row['نوع الخطأ'])
            
            # ترجمة أنواع الأخطاء للإنجليزية للتقرير (شاملة أخطاء V4)
            if 'تكرار في المعرف الفريد' in err_type: err_type = 'Duplicated Primary Key'
            elif 'بيانات إلزامية مفقودة' in err_type: err_type = 'Missing Mandatory Data'
            elif 'صيغة خاطئة' in err_type: err_type = 'Invalid Format (Regex Mismatch)'
            elif 'تناقض:' in err_type: err_type = 'Cross-Column Contradiction'
            elif 'مخالفة شرط' in err_type: err_type = 'Cross-Logic Violation'
            
            # قص النص إذا كان طويلاً جداً حتى لا يشوه الجدول
            err_type = err_type[:60] 
            
            err_count = str(row['عدد السجلات المتأثرة'])
            pdf.cell(130, 10, txt=err_type, border=1, align='L')
            pdf.cell(60, 10, txt=err_count, border=1, ln=1, align='C')

    return bytes(pdf.output())

# ==========================================
# 1. إعدادات الصفحة وتهيئة المتغيرات
# ==========================================
st.set_page_config(page_title="المُقيّم الذكي V4", page_icon="🚀", layout="wide")

if 'dynamic_rules' not in st.session_state:
    st.session_state.dynamic_rules = []
if 'compare_rules' not in st.session_state:
    st.session_state.compare_rules = []

def add_rule(): st.session_state.dynamic_rules.append({"id": str(uuid.uuid4())})
def remove_rule(rule_id): st.session_state.dynamic_rules = [r for r in st.session_state.dynamic_rules if r['id'] != rule_id]

def add_compare_rule(): st.session_state.compare_rules.append({"id": str(uuid.uuid4())})
def remove_compare_rule(rule_id): st.session_state.compare_rules = [r for r in st.session_state.compare_rules if r['id'] != rule_id]

# تنسيقات CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    * { font-family: 'Tajawal', sans-serif; }
    body { direction: RTL; text-align: right; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p { font-size: 1.1rem; font-weight: bold; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .metric-card h3 { margin: 0; font-size: 1.5rem; }
    .metric-card h1 { margin: 10px 0 0 0; font-size: 3rem; font-weight: bold; }
    .rule-container { border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px; margin-bottom: 10px; background-color: #f8f9fa; border-right: 4px solid #764ba2; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. القائمة الجانبية
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2875/2875071.png", width=80)
    st.title("إعدادات البيانات")
    uploaded_file = st.file_uploader("📁 ارفع ملفك (CSV/Excel)", type=['csv', 'xlsx'])
    
    if st.button("🗑️ إعادة ضبط كل القواعد"):
        st.session_state.dynamic_rules = []
        st.session_state.compare_rules = []
        st.rerun()

@st.cache_data
def load_data(file):
    if file.name.endswith('.csv'): return pd.read_csv(file)
    else: return pd.read_excel(file)

# ==========================================
# 3. واجهة التطبيق
# ==========================================
if uploaded_file is None:
    st.info("يرجى رفع ملف بيانات من القائمة الجانبية للبدء 👈")
else:
    df = load_data(uploaded_file)
    columns = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    st.title(f"🚀 تحليل بيانات: {uploaded_file.name}")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 1. التحليل الإحصائي (Profiling)", 
        "🛡️ 2. القواعد الأساسية والصيغ", 
        "🔗 3. القواعد المنطقية المترابطة", 
        "🎯 4. لوحة النتائج"
    ])

    # ---------------------------------------------------------
    # التبويب الأول: التحليل الإحصائي (Data Profiling)
    # ---------------------------------------------------------
    with tab1:
        st.header("الفحص الإحصائي العميق للبيانات")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("إجمالي السجلات", f"{len(df):,}")
        col2.metric("إجمالي الأعمدة", len(columns))
        col3.metric("الخلايا المفقودة كلياً", f"{df.isnull().sum().sum():,}")
        
        st.markdown("---")
        st.subheader("تحليل جودة الأعمدة")
        
        profile_df = pd.DataFrame({
            'العمود': columns,
            'نوع البيانات': [str(df[c].dtype) for c in columns],
            'القيم المفقودة (%)': [(df[c].isnull().sum() / len(df) * 100).round(2) for c in columns],
            'القيم الفريدة': [df[c].nunique() for c in columns]
        })
        st.dataframe(profile_df.style.background_gradient(subset=['القيم المفقودة (%)'], cmap='Reds'), use_container_width=True)

        if numeric_cols:
            st.subheader("التوزيع الإحصائي (للأرقام)")
            selected_num_col = st.selectbox("اختر عموداً رقمياً لعرض توزيعه:", numeric_cols)
            fig_hist = px.histogram(df, x=selected_num_col, marginal="box", title=f"توزيع البيانات في عمود: {selected_num_col}")
            st.plotly_chart(fig_hist, use_container_width=True)

    # ---------------------------------------------------------
    # التبويب الثاني: الأساسيات والصيغ (Regex)
    # ---------------------------------------------------------
    with tab2:
        st.header("معايير الجودة الأساسية")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("🔑 التفرد")
            primary_key = st.selectbox("اختر المعرف الفريد:", ["بدون تحديد"] + columns)
        with col_b:
            st.subheader("📝 الاكتمال")
            mandatory_cols = st.multiselect("اختر الأعمدة الإلزامية:", columns)

        st.markdown("---")
        st.subheader("أรูปแบบ التحقق من الصيغ (Pattern Validation)")
        st.write("التأكد من أن البيانات مكتوبة بصيغة صحيحة (مثل البريد الإلكتروني أو الأرقام).")
        
        regex_patterns = {
            "بريد إلكتروني (Email)": r'^[\w\.-]+@[\w\.-]+\.\w+$',
            "أرقام فقط (Digits)": r'^\d+$',
            "نصوص فقط (Letters)": r'^[a-zA-Zأ-ي\s]+$',
        }
        
        col_regex1, col_regex2 = st.columns(2)
        with col_regex1:
            regex_col = st.selectbox("اختر العمود المطلوب التحقق منه:", ["بدون تحديد"] + columns, key='regex_col')
        with col_regex2:
            regex_type = st.selectbox("اختر الصيغة المطلوبة:", list(regex_patterns.keys()), key='regex_type')

    # ---------------------------------------------------------
    # التبويب الثالث: القواعد المترابطة والمقارنات
    # ---------------------------------------------------------
    with tab3:
        st.header("المحرك المنطقي المتقدم")
        
        st.subheader("أولاً: مقارنة الأعمدة (Cross-Column Comparison)")
        st.button("➕ إضافة قاعدة مقارنة", on_click=add_compare_rule, type="secondary")
        
        for index, rule in enumerate(st.session_state.compare_rules):
            st.markdown(f"<div class='rule-container'>", unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns([3, 2, 3, 1])
            rule_id = rule['id']
            with col1:
                comp_col1 = st.selectbox("العمود الأول:", columns, key=f"comp1_{rule_id}")
            with col2:
                operator = st.selectbox("يجب أن يكون:", ["> (أكبر من)", "< (أصغر من)", "== (يساوي)", "!= (لا يساوي)"], key=f"op_{rule_id}")
            with col3:
                comp_col2 = st.selectbox("مقارنة بـ العمود الثاني:", columns, key=f"comp2_{rule_id}")
            with col4:
                st.write("")
                st.write("")
                st.button("❌", key=f"del_c_{rule_id}", on_click=remove_compare_rule, args=(rule_id,))
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        
        st.subheader("ثانياً: الترابط الشرطي (If This Then That)")
        st.button("➕ إضافة قاعدة شرطية", on_click=add_rule, type="secondary")
        
        for index, rule in enumerate(st.session_state.dynamic_rules):
            st.markdown(f"<div class='rule-container'>", unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns([3, 3, 3, 1])
            rule_id = rule['id']
            with col1:
                cond_col = st.selectbox("إذا كان العمود:", columns, key=f"cond_col_{rule_id}")
            with col2:
                unique_vals = df[cond_col].dropna().unique().tolist() if cond_col else []
                cond_val = st.selectbox("يساوي القيمة:", unique_vals, key=f"cond_val_{rule_id}")
            with col3:
                target_col = st.selectbox("فإن (النتيجة) يجب ألا يكون فارغاً:", columns, key=f"target_col_{rule_id}")
            with col4:
                st.write("")
                st.write("")
                st.button("❌", key=f"del_{rule_id}", on_click=remove_rule, args=(rule_id,))
            st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # التبويب الرابع: التحليل والنتائج مع التصدير (PDF)
    # ---------------------------------------------------------
    with tab4:
        st.header("📊 التقرير النهائي لجودة البيانات")
        analyze_btn = st.button("🚀 تشغيل محرك التحليل الشامل", use_container_width=True, type="primary")
        
        if analyze_btn:
            total_rows = len(df)
            errors = {} 
            
            with st.spinner('جاري طحن البيانات وفحص القواعد المعقدة...'):
                # 1. الأساسيات
                if primary_key != "بدون تحديد":
                    dup_mask = df.duplicated(subset=[primary_key], keep=False)
                    if dup_mask.sum() > 0: errors['تكرار في المعرف الفريد'] = df[dup_mask]
                
                if mandatory_cols:
                    miss_mask = df[mandatory_cols].isnull().any(axis=1)
                    if miss_mask.sum() > 0: errors['بيانات إلزامية مفقودة'] = df[miss_mask]

                # 2. التحقق من الصيغ (Regex)
                if regex_col != "بدون تحديد":
                    pattern = regex_patterns[regex_type]
                    valid_mask = df[regex_col].astype(str).str.match(pattern, na=False)
                    not_null_mask = df[regex_col].notnull()
                    invalid_format = df[~valid_mask & not_null_mask]
                    if len(invalid_format) > 0:
                        errors[f'صيغة خاطئة ({regex_col}) لا تطابق {regex_type}'] = invalid_format

                # 3. قواعد المقارنة (Cross-Column)
                for index, rule in enumerate(st.session_state.compare_rules):
                    rule_id = rule['id']
                    c1 = st.session_state[f"comp1_{rule_id}"]
                    op = st.session_state[f"op_{rule_id}"]
                    c2 = st.session_state[f"comp2_{rule_id}"]
                    try:
                        if ">" in op: err_mask = ~(df[c1] > df[c2]) & df[c1].notnull() & df[c2].notnull()
                        elif "<" in op: err_mask = ~(df[c1] < df[c2]) & df[c1].notnull() & df[c2].notnull()
                        elif "==" in op: err_mask = ~(df[c1] == df[c2]) & df[c1].notnull() & df[c2].notnull()
                        else: err_mask = ~(df[c1] != df[c2]) & df[c1].notnull() & df[c2].notnull()
                        
                        if err_mask.sum() > 0:
                            errors[f'تناقض: {c1} {op} {c2}'] = df[err_mask]
                    except Exception as e:
                        st.error(f"خطأ في مقارنة {c1} مع {c2}. تأكد من توافق أنواع البيانات.")

                # 4. الترابط الشرطي
                for index, rule in enumerate(st.session_state.dynamic_rules):
                    rule_id = rule['id']
                    c_col = st.session_state[f"cond_col_{rule_id}"]
                    c_val = st.session_state[f"cond_val_{rule_id}"]
                    t_col = st.session_state[f"target_col_{rule_id}"]
                    
                    cross_mask = (df[c_col] == c_val) & (df[t_col].isnull())
                    if cross_mask.sum() > 0:
                        errors[f'مخالفة شرط ({c_col}={c_val} -> {t_col} مفقود)'] = df[cross_mask]

            # عرض النتائج
            if not errors:
                st.success("🎉 مذهل! اجتازت بياناتك جميع الفحوصات الصارمة بنجاح.")
                st.balloons()
                quality_score = 100.0
                error_summary = pd.DataFrame(columns=['نوع الخطأ', 'عدد السجلات المتأثرة'])
                
                # تحميل PDF بحالة النجاح 100%
                pdf_data = create_pdf(quality_score, error_summary, total_rows)
                st.download_button(
                    label="📥 تحميل تقرير الجودة (PDF)",
                    data=pdf_data,
                    file_name="Data_Quality_Report_Perfect.pdf",
                    mime="application/pdf"
                )
            else:
                total_error_records = sum([len(e) for e in errors.values()])
                quality_score = max(0, 100 - ((total_error_records / (total_rows * max(len(errors), 1))) * 100))
                
                st.markdown(f"""
                <div class="metric-card">
                    <h3>المؤشر الشامل لجودة البيانات (DQ Score)</h3>
                    <h1>{quality_score:.1f}%</h1>
                </div>
                <br>
                """, unsafe_allow_html=True)
                
                error_summary = pd.DataFrame({'نوع الخطأ': list(errors.keys()), 'عدد السجلات المتأثرة': [len(e) for e in errors.values()]})
                
                # قسم تصدير التقرير PDF
                st.markdown("---")
                st.subheader("🖨️ طباعة النتائج")
                with st.spinner('جاري إنشاء ملف PDF...'):
                    pdf_data = create_pdf(quality_score, error_summary, total_rows)
                    st.download_button(
                        label="📥 تحميل التقرير النهائي (PDF)",
                        data=pdf_data,
                        file_name="Data_Quality_Report.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                st.markdown("---")

                # رسم بياني
                fig = px.bar(error_summary, x='نوع الخطأ', y='عدد السجلات المتأثرة', color='نوع الخطأ', text_auto=True, title="ملخص الأخطاء المكتشفة")
                fig.update_layout(showlegend=False, font=dict(family="Tajawal"))
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("🔍 تفاصيل الأخطاء للتحميل:")
                for err_name, err_df in errors.items():
                    with st.expander(f"🔴 {err_name} ({len(err_df)} سجل)"):
                        st.dataframe(err_df, use_container_width=True)
                        csv = err_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(label="📥 تحميل لتصحيح البيانات", data=csv, file_name=f"errors_{err_name}.csv", mime="text/csv", key=f"dl_{err_name}")
