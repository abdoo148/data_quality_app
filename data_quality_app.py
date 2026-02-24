import streamlit as st
import pandas as pd
import io

# ==========================================
# إعدادات الصفحة الأساسية
# ==========================================
st.set_page_config(
    page_title="مُقيّم جودة البيانات الذكي",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# إضافة بعض التنسيقات (CSS) لتحسين المظهر ودعم الاتجاه من اليمين لليسار (RTL) بشكل أفضل
st.markdown("""
    <style>
    body { direction: RTL; text-align: right; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# عنوان التطبيق والمقدمة
# ==========================================
st.title("📊 تطبيق التقييم العميق لجودة البيانات")
st.markdown("هذا التطبيق يساعدك على تحليل جودة بياناتك ليس فقط آلياً، بل **بناءً على فهمك لقواعد العمل (Business Rules)** الخاصة ببياناتك.")

# ==========================================
# دالة مساعدة لتحميل الملفات
# ==========================================
@st.cache_data
def load_data(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(uploaded_file)
        else:
            return None
        return df
    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة الملف: {e}")
        return None

# ==========================================
# المرحلة الأولى: رفع الملف
# ==========================================
st.header("1. رفع ملف البيانات 📁")
uploaded_file = st.file_uploader("قم برفع ملف البيانات (CSV أو Excel)", type=['csv', 'xlsx', 'xls'])

if uploaded_file is not None:
    # قراءة البيانات
    df = load_data(uploaded_file)
    
    if df is not None:
        st.success(f"تم تحميل الملف بنجاح! يحتوي الملف على {df.shape[0]} صف و {df.shape[1]} عمود.")
        
        with st.expander("👀 نظرة سريعة على عينة من البيانات"):
            st.dataframe(df.head())

        # ==========================================
        # المرحلة الثانية: الأسئلة التفاعلية (قواعد العمل)
        # ==========================================
        st.header("2. تحديد معايير جودة البيانات 📝")
        st.markdown("يرجى الإجابة على الأسئلة التالية لتحديد معايير الجودة الخاصة بهذه البيانات:")
        
        columns = df.columns.tolist()
        numeric_columns = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        
        # إنشاء نموذج (Form) لجمع إجابات المستخدم
        with st.form("dq_rules_form"):
            st.subheader("معيار التفرد (Uniqueness)")
            # السؤال الأول: المعرف الفريد
            primary_key = st.selectbox(
                "ما هو العمود الذي يمثل المعرّف الفريد لكل صف (مثل: رقم الهوية، كود المنتج) ولا يجب أن يتكرر أبداً؟",
                options=["لا يوجد"] + columns
            )
            
            st.subheader("معيار الاكتمال (Completeness)")
            # السؤال الثاني: الأعمدة الإلزامية
            mandatory_columns = st.multiselect(
                "ما هي الأعمدة الإلزامية التي يُمنع منعاً باتاً أن تكون فارغة (Null/Empty)؟",
                options=columns
            )
            
            st.subheader("معيار الصلاحية (Validity)")
            # السؤال الثالث: القيم السالبة (للأعمدة الرقمية فقط)
            if numeric_columns:
                positive_only_columns = st.multiselect(
                    "هل هناك أعمدة رقمية يجب أن تكون قيمها موجبة دائماً (مثل: السعر، العمر، الكمية)؟",
                    options=numeric_columns
                )
            else:
                positive_only_columns = []
                st.info("لا توجد أعمدة رقمية في هذا الملف لتطبيق هذا المعيار.")
                
            # زر بدء التحليل
            analyze_button = st.form_submit_button("🚀 بدء التحليل العميق بناءً على إجاباتي")

        # ==========================================
        # المرحلة الثالثة: التحليل العميق واستخراج النتائج
        # ==========================================
        if analyze_button:
            st.markdown("---")
            st.header("3. تقرير جودة البيانات التفصيلي 📈")
            
            # تهيئة متغيرات لحساب النقاط (Scoring)
            total_rows = len(df)
            issues_found = False
            
            # 1. تحليل التفرد (Uniqueness)
            if primary_key != "لا يوجد":
                st.subheader(f"🔍 تحليل التفرد لعمود: `{primary_key}`")
                duplicated_rows = df[df.duplicated(subset=[primary_key], keep=False)]
                duplicate_count = len(duplicated_rows)
                
                if duplicate_count > 0:
                    uniqueness_score = ((total_rows - duplicate_count) / total_rows) * 100
                    st.warning(f"تم العثور على {duplicate_count} صف يحتوي على قيم مكررة في عمود المعرف الفريد!")
                    st.metric("نسبة التفرد (Uniqueness Score)", f"{uniqueness_score:.1f}%")
                    with st.expander("عرض السجلات المكررة"):
                        st.dataframe(duplicated_rows.sort_values(by=primary_key))
                    issues_found = True
                else:
                    st.success("ممتاز! لا يوجد أي تكرار في عمود المعرف الفريد. (نسبة التفرد: 100%)")
            
            # 2. تحليل الاكتمال (Completeness)
            if mandatory_columns:
                st.subheader("🔍 تحليل الاكتمال للأعمدة الإلزامية")
                
                # البحث عن الصفوف التي تحتوي على قيم فارغة في الأعمدة المحددة
                missing_data_mask = df[mandatory_columns].isnull().any(axis=1)
                missing_rows = df[missing_data_mask]
                missing_count = len(missing_rows)
                
                if missing_count > 0:
                    completeness_score = ((total_rows - missing_count) / total_rows) * 100
                    st.warning(f"تم العثور على {missing_count} صف يحتوي على بيانات مفقودة في الأعمدة الإلزامية!")
                    st.metric("نسبة الاكتمال (Completeness Score)", f"{completeness_score:.1f}%")
                    
                    # تفصيل الأعمدة المفقودة
                    missing_stats = df[mandatory_columns].isnull().sum()
                    missing_stats = missing_stats[missing_stats > 0]
                    st.write("تفصيل النواقص حسب العمود:")
                    st.bar_chart(missing_stats)
                    
                    with st.expander("عرض السجلات التي بها بيانات إلزامية مفقودة"):
                        st.dataframe(missing_rows)
                    issues_found = True
                else:
                    st.success("رائع! جميع الأعمدة الإلزامية مكتملة بنسبة 100%.")

            # 3. تحليل الصلاحية المنطقية (Validity - Positive Values)
            if positive_only_columns:
                st.subheader("🔍 تحليل صلاحية الأرقام (القيم الموجبة فقط)")
                
                invalid_rows_list = []
                for col in positive_only_columns:
                    # استخراج الصفوف التي تحتوي على قيم أصغر من الصفر
                    invalid = df[df[col] < 0]
                    if not invalid.empty:
                        invalid_rows_list.append((col, invalid))
                
                if invalid_rows_list:
                    st.error("تم العثور على قيم سالبة غير منطقية بناءً على تحديدك!")
                    for col, invalid_df in invalid_rows_list:
                        st.write(f"- عمود `{col}` يحتوي على **{len(invalid_df)}** قيمة سالبة.")
                        with st.expander(f"عرض القيم السالبة في {col}"):
                            st.dataframe(invalid_df)
                    issues_found = True
                else:
                    st.success("تم التحقق! جميع القيم في الأعمدة المحددة موجبة ومنطقية بنسبة 100%.")

            # الخلاصة النهائية
            st.markdown("---")
            if not issues_found:
                st.balloons()
                st.success("🎉 تهانينا! بناءً على المعايير التي حددتها، بياناتك في حالة ممتازة وتخلو من الأخطاء الحرجة.")
            else:
                st.info("💡 **نصيحة:** يرجى مراجعة السجلات المعروضة أعلاه وتصحيحها في الملف الأصلي لضمان جودة بياناتك قبل استخدامها في التحليلات أو النماذج.")
