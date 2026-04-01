import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import uuid
import re
import io
from fpdf import FPDF

# ==========================================
# 0. دوال مساعدة (توليد PDF والتعرف الذكي)
# ==========================================
def create_pdf(quality_score, error_summary, total_rows, error_chart=None):
    """إنشاء ملف PDF يحتوي على ملخص الأخطاء ورسومات بيانية بالإنجليزية"""
    pdf = FPDF()
    pdf.add_page()
    
    # Header - العنوان الرئيسي
    pdf.set_fill_color(118, 75, 162) # اللون البنفسجي الخاص بالتطبيق
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 24)
    pdf.cell(0, 20, txt="Data Quality Report", ln=1, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(25)
    
    # Executive Summary - الملخص التنفيذي
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, txt="1. Executive Summary", ln=1, align='L')
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, txt=f"Total Records Analyzed: {total_rows}", ln=1)
    pdf.cell(0, 8, txt=f"Data Quality Score: {quality_score:.1f}%", ln=1)
    
    # Progress Bar Shape - شكل شريط التقدم في PDF
    pdf.ln(5)
    pdf.set_draw_color(200, 200, 200)
    pdf.rect(10, pdf.get_y(), 100, 5)
    pdf.set_fill_color(0, 200, 0) if quality_score > 80 else pdf.set_fill_color(255, 0, 0)
    pdf.rect(10, pdf.get_y(), quality_score if quality_score > 0 else 0.1, 5, 'F')
    pdf.ln(10)
    
    # Charts Section - قسم الرسومات البيانية
    if error_chart is not None:
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, txt="2. Visual Error Distribution", ln=1, align='L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # تحويل رسم Plotly إلى صورة وإضافتها
        img_bytes = pio.to_image(error_chart, format="png", width=800, height=400)
        img_buffer = io.BytesIO(img_bytes)
        pdf.image(img_buffer, x=10, y=None, w=180)
        pdf.ln(5)

    # Detailed Table - جدول التفاصيل
    if not error_summary.empty:
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, txt="3. Detailed Error Summary", ln=1, align='L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        pdf.set_font('Arial', 'B', 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(130, 10, txt='Error Categorization', border=1, align='C', fill=True)
        pdf.cell(60, 10, txt='Affected Rows', border=1, ln=1, align='C', fill=True)
        
        pdf.set_font('Arial', '', 11)
        for index, row in error_summary.iterrows():
            err_type = str(row['نوع الخطأ'])
            # ترجمة بسيطة للتقرير
            if 'تكرار' in err_type: err_type = 'Uniqueness Violation'
            elif 'مفقودة' in err_type: err_type = 'Missing Mandatory Values'
            elif 'صيغة' in err_type: err_type = 'Pattern/Regex Mismatch'
            elif 'تناقض' in err_type: err_type = 'Logical Contradiction'
            else: err_type = 'Business Logic Error'
            
            pdf.cell(130, 10, txt=err_type, border=1)
            pdf.cell(60, 10, txt=str(row['عدد السجلات المتأثرة']), border=1, ln=1, align='C')

    return pdf.output().encode('latin-1')

def suggest_primary_key(df):
    """محرك ذكي لاقتراح المعرف الفريد بناءً على الاسم وخصائص البيانات"""
    keywords = ['id', 'code', 'no', 'number', 'key', 'identifer', 'رقم', 'كود', 'معرف', 'هوية', 'سيريال']
    columns = df.columns.tolist()
    for col in columns:
        col_lower = str(col).lower()
        if any(kw in col_lower for kw in keywords):
            if df[col].nunique() == len(df) and df[col].notnull().all():
                return col
    for col in columns:
        if df[col].nunique() == len(df) and df[col].notnull().all():
            return col
    return "بدون تحديد"

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
    div[data-testid="stExpander"] { direction: rtl; }
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
    if uploaded_file is not None and uploaded_file.name.endswith(('.xlsx', '.xls')):
        try:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            if len(sheet_names) > 1:
                selected_sheet = st.selectbox("📑 اختر ورقة العمل (Sheet):", sheet_names)
            else:
                selected_sheet = sheet_names[0]
        except:
            st.error("حدث خطأ في قراءة أوراق العمل.")
    
    if st.button("🗑️ إعادة ضبط كل القواعد"):
        st.session_state.dynamic_rules = []
        st.session_state.compare_rules = []
        st.rerun()

@st.cache_data
def load_data(file, sheet_name=None):
    if file.name.endswith('.csv'): return pd.read_csv(file)
    else: return pd.read_excel(file, sheet_name=sheet_name)

# ==========================================
# 3. واجهة التطبيق
# ==========================================
if uploaded_file is None:
    st.info("يرجى رفع ملف بيانات من القائمة الجانبية للبدء 👈")
else:
    df = load_data(uploaded_file, selected_sheet)
    columns = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    st.title(f"🚀 تحليل ذكي لملف: {uploaded_file.name}")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 1. التحليل الإحصائي (Profiling)", 
        "🛡️ 2. القواعد الأساسية والصيغ", 
        "🔗 3. القواعد المنطقية المترابطة", 
        "🎯 4. لوحة النتائج"
    ])

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
        
        st.dataframe(
            profile_df,
            column_config={
                "القيم المفقودة (%)": st.column_config.ProgressColumn(
                    "القيم المفقودة (%)", help="نسبة الفراغات في العمود المئوية",
                    format="%.2f%%", min_value=0, max_value=100,
                )
            },
            use_container_width=True
        )

        if numeric_cols:
            st.subheader("التوزيع الإحصائي (للأرقام)")
            selected_num_col = st.selectbox("اختر عموداً رقمياً لعرض توزيعه:", numeric_cols)
            fig_hist = px.histogram(df, x=selected_num_col, marginal="box", title=f"توزيع البيانات في عمود: {selected_num_col}")
            st.plotly_chart(fig_hist, use_container_width=True)

    with tab2:
        st.header("معايير الجودة الأساسية")
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("🔑 التفرد (Uniqueness)")
            suggested_pk = suggest_primary_key(df)
            options = ["بدون تحديد"] + columns
            pk_index = options.index(suggested_pk) if suggested_pk in options else 0
            primary_key = st.selectbox("اختر المعرف الفريد (ID):", options, index=pk_index)
            if suggested_pk != "بدون تحديد": st.caption(f"✨ تم التعرف تلقائياً على `{suggested_pk}` كمعرف فريد.")
            
        with col_b:
            st.subheader("📝 الاكتمال (Completeness)")
            mandatory_cols = st.multiselect("الأعمدة الإلزامية التي يجب فحص اكتمالها:", columns, default=columns)

        st.markdown("---")
        st.subheader("أنماط التحقق من الصيغ (Pattern Validation)")
        regex_patterns = {
            "بريد إلكتروني (Email)": r'^[\w\.-]+@[\w\.-]+\.\w+$',
            "أرقام فقط (Digits)": r'^\d+$',
            "نصوص فقط (Letters)": r'^[a-zA-Zأ-ي\s]+$',
        }
        col_regex1, col_regex2 = st.columns(2)
        with col_regex1: regex_col = st.selectbox("اختر العمود المطلوب فحص صيغته:", ["بدون تحديد"] + columns, key='regex_col')
        with col_regex2: regex_type = st.selectbox("الصيغة المطلوبة:", list(regex_patterns.keys()), key='regex_type')

    with tab3:
        st.header("المحرك المنطقي المتقدم")
        st.subheader("أولاً: مقارنة الأعمدة")
        st.button("➕ إضافة قاعدة مقارنة", on_click=add_compare_rule, type="secondary")
        for index, rule in enumerate(st.session_state.compare_rules):
            st.markdown(f"<div class='rule-container'>", unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns([3, 2, 3, 1])
            rule_id = rule['id']
            with col1: st.selectbox("العمود الأول:", columns, key=f"comp1_{rule_id}")
            with col2: st.selectbox("يجب أن يكون:", ["> (أكبر من)", "< (أصغر من)", "== (يساوي)", "!= (لا يساوي)"], key=f"op_{rule_id}")
            with col3: st.selectbox("مقارنة بـ العمود الثاني:", columns, key=f"comp2_{rule_id}")
            with col4:
                st.write("")
                st.button("❌", key=f"del_c_{rule_id}", on_click=remove_compare_rule, args=(rule_id,))
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("ثانياً: الترابط الشرطي")
        st.button("➕ إضافة قاعدة شرطية", on_click=add_rule, type="secondary")
        for index, rule in enumerate(st.session_state.dynamic_rules):
            st.markdown(f"<div class='rule-container'>", unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns([3, 3, 3, 1])
            rule_id = rule['id']
            with col1: c_col = st.selectbox("إذا كان العمود:", columns, key=f"cond_col_{rule_id}")
            with col2:
                unique_vals = df[c_col].dropna().unique().tolist() if c_col else []
                st.selectbox("يساوي القيمة:", unique_vals, key=f"cond_val_{rule_id}")
            with col3: st.selectbox("فإن (النتيجة) يجب ألا يكون فارغاً:", columns, key=f"target_col_{rule_id}")
            with col4:
                st.write("")
                st.button("❌", key=f"del_{rule_id}", on_click=remove_rule, args=(rule_id,))
            st.markdown("</div>", unsafe_allow_html=True)

    with tab4:
        st.header("📊 التقرير النهائي لجودة البيانات")
        analyze_btn = st.button("🚀 تشغيل محرك التحليل الشامل", use_container_width=True, type="primary")
        
        if analyze_btn:
            total_rows = len(df)
            errors = {} 
            with st.spinner('جاري تحليل البيانات...'):
                if primary_key != "بدون تحديد":
                    dup_mask = df.duplicated(subset=[primary_key], keep=False)
                    if dup_mask.sum() > 0: errors['تكرار في المعرف الفريد'] = df[dup_mask]
                if mandatory_cols:
                    miss_mask = df[mandatory_cols].isnull().any(axis=1)
                    if miss_mask.sum() > 0: errors['بيانات إلزامية مفقودة'] = df[miss_mask]
                if regex_col != "بدون تحديد":
                    pattern = regex_patterns[regex_type]
                    valid_mask = df[regex_col].astype(str).str.match(pattern, na=False)
                    invalid_format = df[~valid_mask & df[regex_col].notnull()]
                    if len(invalid_format) > 0: errors[f'صيغة خاطئة في ({regex_col})'] = invalid_format

                for rule in st.session_state.compare_rules:
                    rule_id = rule['id']
                    c1, op, c2 = st.session_state[f"comp1_{rule_id}"], st.session_state[f"op_{rule_id}"], st.session_state[f"comp2_{rule_id}"]
                    try:
                        if ">" in op: err_mask = ~(df[c1] > df[c2])
                        elif "<" in op: err_mask = ~(df[c1] < df[c2])
                        elif "==" in op: err_mask = ~(df[c1] == df[c2])
                        else: err_mask = ~(df[c1] != df[c2])
                        err_mask = err_mask & df[c1].notnull() & df[c2].notnull()
                        if err_mask.sum() > 0: errors[f'تناقض: {c1} {op} {c2}'] = df[err_mask]
                    except: pass

                for rule in st.session_state.dynamic_rules:
                    rule_id = rule['id']
                    c_col, c_val, t_col = st.session_state[f"cond_col_{rule_id}"], st.session_state[f"cond_val_{rule_id}"], st.session_state[f"target_col_{rule_id}"]
                    cross_mask = (df[c_col] == c_val) & (df[t_col].isnull())
                    if cross_mask.sum() > 0: errors[f'مخالفة شرط ({c_col}={c_val})'] = df[cross_mask]

            if not errors:
                st.success("🎉 بياناتك مطابقة تماماً لجميع المعايير والشروط!")
                st.balloons()
            else:
                total_error_records = sum([len(e) for e in errors.values()])
                quality_score = max(0, 100 - ((total_error_records / (total_rows * max(len(errors), 1))) * 100))
                st.markdown(f'<div class="metric-card"><h3>مؤشر جودة البيانات الشامل</h3><h1>{quality_score:.1f}%</h1></div><br>', unsafe_allow_html=True)
                
                error_summary = pd.DataFrame({'نوع الخطأ': list(errors.keys()), 'عدد السجلات المتأثرة': [len(e) for e in errors.values()]})
                
                # إنشاء الرسم البياني لحفظه في الـ PDF
                fig = px.bar(error_summary, x='نوع الخطأ', y='عدد السجلات المتأثرة', color='نوع الخطأ', text_auto=True, title="Visual Error Summary")
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("🖨️ طباعة التقرير الاحترافي")
                with st.spinner('جاري إنشاء تقرير PDF يحتوي على رسومات بيانية...'):
                    pdf_data = create_pdf(quality_score, error_summary, total_rows, error_chart=fig)
                    st.download_button("📥 تحميل التقرير التفصيلي (PDF + Charts)", data=pdf_data, file_name="Comprehensive_DQ_Report.pdf", mime="application/pdf", use_container_width=True)

                for err_name, err_df in errors.items():
                    with st.expander(f"🔴 {err_name} ({len(err_df)} سجل)"):
                        st.dataframe(err_df, use_container_width=True)
                        csv = err_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(f"📥 تحميل سجلات: {err_name}", data=csv, file_name=f"{err_name}.csv", mime="text/csv", key=f"dl_{err_name}")
