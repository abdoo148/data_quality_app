import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# 1. إعدادات الصفحة والتصميم (UI/UX)
# ==========================================
st.set_page_config(page_title="المُقيّم الذكي V2", page_icon="✨", layout="wide")

# CSS مخصص لتحسين الواجهة ودعم اللغة العربية (RTL) والألوان
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    * { font-family: 'Tajawal', sans-serif; }
    body { direction: RTL; text-align: right; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem;
        font-weight: bold;
    }
    .metric-card {
        background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card h3 { margin: 0; font-size: 1.5rem; }
    .metric-card h1 { margin: 10px 0 0 0; font-size: 3rem; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. القائمة الجانبية (رفع الملفات والإعدادات)
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2875/2875071.png", width=100)
    st.title("إعدادات البيانات")
    uploaded_file = st.file_uploader("📁 ارفع ملفك هنا (CSV/Excel)", type=['csv', 'xlsx'])
    
    st.markdown("---")
    st.info("💡 **كيف يعمل التطبيق؟**\n1. ارفع الملف\n2. استكشف البيانات\n3. ضع القواعد\n4. احصل على التقرير التفاعلي")

@st.cache_data
def load_data(file):
    if file.name.endswith('.csv'): return pd.read_csv(file)
    else: return pd.read_excel(file)

# ==========================================
# 3. واجهة التطبيق الرئيسية (التبويبات)
# ==========================================
if uploaded_file is None:
    st.markdown("<h1 style='text-align: center; color: #888; margin-top: 100px;'>يرجى رفع ملف بيانات من القائمة الجانبية للبدء 👈</h1>", unsafe_allow_html=True)
else:
    df = load_data(uploaded_file)
    columns = df.columns.tolist()
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    # استخراج الأعمدة النصية التي تحتوي على تصنيفات (أقل من 20 قيمة فريدة)
    cat_cols = [c for c in df.columns if df[c].dtype == 'object' and df[c].nunique() < 20]

    st.title(f"✨ تحليل بيانات: {uploaded_file.name}")
    
    # إنشاء التبويبات (Tabs)
    tab1, tab2, tab3, tab4 = st.tabs([
        "👁️ 1. نظرة عامة", 
        "📋 2. القواعد الأساسية", 
        "🧠 3. القواعد المترابطة (متقدم)", 
        "🎯 4. لوحة النتائج"
    ])

    # ---------------------------------------------------------
    # التبويب الأول: نظرة عامة
    # ---------------------------------------------------------
    with tab1:
        st.header("استكشاف سريع للبيانات")
        col1, col2, col3 = st.columns(3)
        col1.metric("إجمالي الصفوف", f"{len(df):,}")
        col2.metric("إجمالي الأعمدة", len(columns))
        col3.metric("عدد الخلايا الفارغة الكلي", df.isnull().sum().sum())
        
        st.dataframe(df.head(10), use_container_width=True)

    # ---------------------------------------------------------
    # التبويب الثاني: القواعد الأساسية
    # ---------------------------------------------------------
    with tab2:
        st.header("إعدادات الجودة الأساسية")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("🔑 التفرد (Uniqueness)")
            primary_key = st.selectbox("اختر المعرف الفريد (الذي لا يجب أن يتكرر):", ["بدون تحديد"] + columns)
            
        with col_b:
            st.subheader("📝 الاكتمال (Completeness)")
            mandatory_cols = st.multiselect("اختر الأعمدة الإلزامية (لا تقبل الفراغ):", columns)

        st.markdown("---")
        st.subheader("🔢 النطاق المنطقي للأرقام")
        if numeric_cols:
            range_col = st.selectbox("اختر عموداً رقمياً لتحديد نطاقه المسموح:", ["بدون تحديد"] + numeric_cols)
            if range_col != "بدون تحديد":
                min_val, max_val = st.slider(
                    f"حدد النطاق المسموح لـ {range_col}", 
                    float(df[range_col].min()), float(df[range_col].max()), 
                    (float(df[range_col].min()), float(df[range_col].max()))
                )
        else:
            range_col = "بدون تحديد"
            st.info("لا توجد أعمدة رقمية في الملف.")

    # ---------------------------------------------------------
    # التبويب الثالث: القواعد المنطقية المترابطة (الجديد)
    # ---------------------------------------------------------
    with tab3:
        st.header("بناء قواعد عمل معقدة ومترابطة")
        
        col_c, col_d = st.columns(2)
        
        # 1. القيم المسموحة (Categorical Logic)
        with col_c:
            st.subheader("🏷️ تقييد القيم النصية")
            if cat_cols:
                target_cat_col = st.selectbox("اختر عمود تصنيفي (مثال: الحالة، الجنس، القسم):", ["بدون تحديد"] + cat_cols)
                if target_cat_col != "بدون تحديد":
                    unique_vals = df[target_cat_col].dropna().unique().tolist()
                    allowed_vals = st.multiselect(f"ما هي القيم الصحيحة فقط لعمود ({target_cat_col})؟", unique_vals, default=unique_vals)
            else:
                target_cat_col = "بدون تحديد"
                st.info("لا توجد أعمدة تصنيفية مناسبة في الملف.")

        # 2. القاعدة الشرطية المزدوجة (If This Then That)
        with col_d:
            st.subheader("🔗 الارتباط الشرطي بين عمودين")
            st.write("مثال: **إذا** كان عمود [الحالة] يساوي [مغلق] **فإن** عمود [تاريخ الإغلاق] يجب أن يكون ممتلئاً.")
            
            enable_cross_logic = st.checkbox("تفعيل القاعدة الشرطية")
            if enable_cross_logic:
                cond_col = st.selectbox("إذا كان عمود (الشرط):", columns, key="cond_col")
                cond_val = st.selectbox("يساوي القيمة:", df[cond_col].dropna().unique().tolist(), key="cond_val")
                target_cond_col = st.selectbox("فإن عمود (النتيجة) يجب ألا يكون فارغاً:", columns, key="target_cond_col")

    # ---------------------------------------------------------
    # التبويب الرابع: لوحة النتائج التفاعلية
    # ---------------------------------------------------------
    with tab4:
        st.header("📊 التقرير النهائي لجودة البيانات")
        analyze_btn = st.button("🚀 تشغيل محرك التحليل الآن", use_container_width=True, type="primary")
        
        if analyze_btn:
            total_rows = len(df)
            errors = {} # لجمع ملخص الأخطاء
            
            with st.spinner('جاري تحليل البيانات ومعالجة القواعد المنطقية...'):
                
                # 1. فحص التفرد
                if primary_key != "بدون تحديد":
                    dup_mask = df.duplicated(subset=[primary_key], keep=False)
                    if dup_mask.sum() > 0:
                        errors['التكرار'] = df[dup_mask]
                
                # 2. فحص الاكتمال
                if mandatory_cols:
                    miss_mask = df[mandatory_cols].isnull().any(axis=1)
                    if miss_mask.sum() > 0:
                        errors['بيانات مفقودة'] = df[miss_mask]

                # 3. فحص النطاق الرقمي
                if range_col != "بدون تحديد":
                    range_mask = (df[range_col] < min_val) | (df[range_col] > max_val)
                    if range_mask.sum() > 0:
                        errors[f'خارج النطاق ({range_col})'] = df[range_mask]

                # 4. فحص القيم المسموحة
                if cat_cols and target_cat_col != "بدون تحديد" and allowed_vals:
                    cat_mask = ~df[target_cat_col].isin(allowed_vals) & df[target_cat_col].notnull()
                    if cat_mask.sum() > 0:
                        errors['قيم غير مسموحة'] = df[cat_mask]

                # 5. فحص الارتباط الشرطي
                if enable_cross_logic:
                    cross_mask = (df[cond_col] == cond_val) & (df[target_cond_col].isnull())
                    if cross_mask.sum() > 0:
                        errors['مخالفة الشرط المترابط'] = df[cross_mask]

            # عرض النتائج
            if not errors:
                st.success("🎉 ممتاااااز! بياناتك نظيفة تماماً وتتوافق مع جميع القواعد المعقدة التي حددتها.")
                st.balloons()
            else:
                # حساب درجة الجودة العامة
                total_errors = sum([len(e) for e in errors.values()])
                quality_score = max(0, 100 - ((total_errors / (total_rows * max(len(errors), 1))) * 100))
                
                # عرض بطاقة النتيجة
                st.markdown(f"""
                <div class="metric-card">
                    <h3>مؤشر جودة البيانات (Data Quality Score)</h3>
                    <h1>{quality_score:.1f}%</h1>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # عرض رسم بياني للأخطاء
                error_summary = pd.DataFrame({
                    'نوع الخطأ': list(errors.keys()),
                    'عدد الصفوف المتأثرة': [len(e) for e in errors.values()]
                })
                
                fig = px.bar(error_summary, x='نوع الخطأ', y='عدد الصفوف المتأثرة', 
                             color='نوع الخطأ', title="توزيع أخطاء جودة البيانات", text_auto=True)
                fig.update_layout(showlegend=False, font=dict(family="Tajawal"))
                st.plotly_chart(fig, use_container_width=True)

                # عرض التفاصيل
                st.subheader("🔍 تفاصيل السجلات التي تحتوي على أخطاء:")
                for err_name, err_df in errors.items():
                    with st.expander(f"🔴 {err_name} ({len(err_df)} سجل)"):
                        st.dataframe(err_df, use_container_width=True)
                        
                        # زر لتحميل الأخطاء كملف CSV
                        csv = err_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 تحميل هذه السجلات لتصحيحها",
                            data=csv,
                            file_name=f"errors_{err_name}.csv",
                            mime="text/csv"
                        )
