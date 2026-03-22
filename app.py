import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image

# 1. הגדרות עמוד
try:
    favicon = Image.open('politex.ico')
    st.set_page_config(page_title="פוליטקס - ניתוח קריאות חוזרות", page_icon=favicon, layout="wide")
except:
    st.set_page_config(page_title="פוליטקס - ניתוח קריאות חוזרות", layout="wide")

# 2. לוגו
try:
    logo = Image.open('logo.png')
    st.image(logo, width=180)
except:
    pass

st.markdown("""
    <style>
    body, .main, .stText { direction: rtl; text-align: right; }
    .stMetric { direction: ltr !important; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 מחשב קריאות חוזרות לפי טכנאי אחראי")

uploaded_file = st.file_uploader("העלה קובץ שירות (XLSX/CSV)", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        # טעינת נתונים
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        else:
            df = pd.read_excel(uploaded_file, engine='calamine')

        # עמודות חובה
        id_col = "מס. קריאה"
        device_col = "מס' מכשיר"
        date_col = "ת. פתיחה"
        tech_col = "לטיפול"

        if all(col in df.columns for col in [id_col, device_col, date_col, tech_col]):
            # עיבוד תאריכים ומיון
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
            df = df.dropna(subset=[device_col, date_col, tech_col]).sort_values([device_col, date_col])

            # --- לוגיקה מתוקנת ---
            # לכל שורה, אנחנו מושכים את הפרטים של הקריאה *הבאה* באותו מכשיר
            df['קריאה_הבאה_תאריך'] = df.groupby(device_col)[date_col].shift(-1)
            df['קריאה_הבאה_מספר'] = df.groupby(device_col)[id_col].shift(-1)
            df['קריאה_הבאה_טכנאי'] = df.groupby(device_col)[tech_col].shift(-1)
            
            # חישוב הפרש ימים לקריאה הבאה
            df['ימים_עד_לקריאה_הבאה'] = (df['קריאה_הבאה_תאריך'] - df[date_col]).dt.total_seconds() / (24 * 3600)
            
            # קריאה נחשבת "נכשלת" (מייצרת חוזרת) אם הקריאה הבאה הגיעה תוך 30 יום
            # האחריות נרשמת על הטכנאי של הקריאה הנוכחית!
            df['ייצר_קריאה_חוזרת'] = ((df['ימים_עד_לקריאה_הבאה'] <= 30) & (df['ימים_עד_לקריאה_הבאה'] >= 0)).astype(int)

            # סטטיסטיקה לפי טכנאי
            # סה"כ קריאות שהטכנאי ביצע לעומת כמה מהן "חזרו" תוך 30 יום
            tech_stats = df.groupby(tech_col).agg({
                id_col: 'count',
                'ייצר_קריאה_חוזרת': 'sum'
            }).reset_index()
            tech_stats.columns = ['טכנאי', 'סה"כ קריאות שביצע', 'קריאות שחזרו (תוך 30 יום)']
            tech_stats['אחוז קריאות חוזרות'] = (tech_stats['קריאות שחזרו (תוך 30 יום)'] / tech_stats['סה"כ קריאות שביצע']) * 100
            
            # מדדים כלליים
            total_system_calls = len(df)
            total_repeats = df['ייצר_קריאה_חוזרת'].sum()
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("סה\"כ קריאות במערכת", f"{total_system_calls}")
            c2.metric("סה\"כ קריאות חוזרות", f"{total_repeats}")
            c3.metric("אחוז חוזרות מחלקתי", f"{(total_repeats/total_system_calls)*100:.1f}%")

            # גרף
            st.subheader("📈 דירוג טכנאים לפי אחוז קריאות חוזרות")
            st.caption("האחוז מחושב מתוך סך הקריאות שהטכנאי ביצע, אשר גררו קריאה נוספת תוך 30 יום.")
            fig = px.bar(tech_stats.sort_values('אחוז קריאות חוזרות', ascending=False), 
                         x='טכנאי', y='אחוז קריאות חוזרות', text_auto='.1f',
                         color='אחוז קריאות חוזרות', color_continuous_scale='Reds')
            st.plotly_chart(fig, use_container_width=True)

            # פירוט פר טכנאי
            st.subheader("🔍 חקירת שרשרת קריאות לפי טכנאי")
            target_tech = st.selectbox("בחר טכנאי כדי לראות אילו קריאות שלו חזרו:", ["בחר טכנאי"] + list(tech_stats['טכנאי'].unique()))
            
            if target_tech != "בחר טכנאי":
                # מציגים את הקריאות שהטכנאי עשה, ומה הייתה הקריאה שחזרה אחריו
                tech_calls_view = df[(df[tech_col] == target_tech) & (df['ייצר_קריאה_חוזרת'] == 1)].copy()
                
                display_df = tech_calls_view[[id_col, date_col, device_col, 'קריאה_הבאה_מספר', 'קריאה_הבאה_תאריך', 'ימים_עד_לקריאה_הבאה', 'קריאה_הבאה_טכנאי']]
                display_df.columns = ['קריאת מקור (שלך)', 'תאריך מקור', 'מספר מכשיר', 'קריאה חוזרת שנוצרה', 'תאריך חוזרת', 'ימים שעברו', 'טכנאי שביצע חוזרת']
                
                st.write(f"נמצאו {len(display_df)} קריאות שבוצעו על ידי {target_tech} וחזרו בתוך 30 יום:")
                st.dataframe(display_df.style.format({'ימים שעברו': '{:.1f}'}), use_container_width=True)

            # הורדה
            st.divider()
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 הורד קובץ ניתוח מלא", csv, "politex_repeat_calls_final.csv", "text/csv")

        else:
            st.error("חסרות עמודות קריטיות בקובץ. וודא שקיימות: מס. קריאה, מס' מכשיר, ת. פתיחה, לטיפול.")
    except Exception as e:
        st.error(f"שגיאה בעיבוד הקובץ: {e}")
