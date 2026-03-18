import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image

# 1. הגדרת עמוד ו-Favicon
try:
    favicon = Image.open('politex.ico')
    st.set_page_config(page_title="ניהול קריאות חוזרות - פוליטקס", page_icon=favicon, layout="wide")
except:
    st.set_page_config(page_title="ניהול קריאות חוזרות", page_icon="📊", layout="wide")

# 2. הצגת לוגו
try:
    logo = Image.open('logo.png')
    st.image(logo, width=180)
except:
    pass

# עיצוב לעברית
st.markdown("""
    <style>
    body, .main, .stText { direction: rtl; text-align: right; }
    .stMetric { direction: ltr !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 ניתוח עומק: קריאות חוזרות")

uploaded_file = st.file_uploader("העלה קובץ קריאות שירות (XLSX/CSV)", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        # טעינת נתונים
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        else:
            df = pd.read_excel(uploaded_file, engine='calamine')

        # הגדרת עמודות
        id_col = "מס. קריאה"
        device_col = "מס' מכשיר"
        date_col = "ת. פתיחה"
        tech_col = "לטיפול"

        if all(col in df.columns for col in [id_col, device_col, date_col]):
            # עיבוד ראשוני
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
            df = df.dropna(subset=[device_col, date_col]).sort_values([device_col, date_col])

            # חישוב קריאה חוזרת + זיהוי קריאת המקור
            df['קריאה קודמת'] = df.groupby(device_col)[id_col].shift(1)
            df['תאריך קודם'] = df.groupby(device_col)[date_col].shift(1)
            df['ימים מהקריאה הקודמת'] = (df[date_col] - df['תאריך קודם']).dt.total_seconds() / (24 * 3600)
            df['האם חוזרת'] = (df['ימים מהקריאה הקודמת'] <= 30).astype(int)

            # מדדים כלליים
            total_calls = len(df)
            repeat_calls = df['האם חוזרת'].sum()
            
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("סה\"כ קריאות", total_calls)
            m2.metric("קריאות חוזרות", repeat_calls)
            m3.metric("אחוז חוזרות כללי", f"{(repeat_calls/total_calls)*100:.1f}%")

            # --- חלק א: ניתוח טכנאים ---
            st.header("👤 ניתוח לפי טכנאי")
            tech_stats = df.groupby(tech_col)['האם חוזרת'].agg(['count', 'sum']).reset_index()
            tech_stats.columns = ['טכנאי', 'סה"כ קריאות', 'חוזרות']
            tech_stats['אחוז חוזרות'] = (tech_stats['חוזרות'] / tech_stats['סה"כ קריאות']) * 100
            
            fig = px.bar(tech_stats.sort_values('אחוז חוזרות', ascending=False), 
                         x='טכנאי', y='אחוז חוזרות', text_auto='.1f', color='אחוז חוזרות',
                         color_continuous_scale='Reds')
            st.plotly_chart(fig, use_container_width=True)

            # --- חלק ב: פירוט שרשראות קריאות ---
            st.header("🔍 פירוט קריאות חוזרות (שרשראות)")
            
            selected_tech = st.selectbox("בחר טכנאי לצפייה בקריאות החוזרות שלו:", ["כל הטכנאים"] + list(tech_stats['טכנאי'].unique()))
            
            # סינון הנתונים להצגת החוזרות בלבד
            view_df = df[df['האם חוזרת'] == 1].copy()
            
            if selected_tech != "כל הטכנאים":
                view_df = view_df[view_df[tech_col] == selected_tech]

            # עיצוב הטבלה להצגה
            display_cols = [id_col, 'קריאה קודמת', device_col, date_col, 'תאריך קודם', 'ימים מהקריאה הקודמת', tech_col]
            
            if not view_df.empty:
                st.write(f"נמצאו {len(view_df)} מקרי קריאות חוזרות עבור הבחירה:")
                st.dataframe(view_df[display_cols].style.format({'ימים מהקריאה הקודמת': '{:.1f}'}), use_container_width=True)
            else:
                st.success("לא נמצאו קריאות חוזרות עבור טכנאי זה.")

            # הורדת קובץ מלא
            st.divider()
            csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 הורד קובץ מעובד מלא (כולל שיוך קריאות)", csv, "full_analysis.csv", "text/csv")

        else:
            st.error("הקובץ חסר עמודות קריטיות (מס. קריאה, מס' מכשיר או ת. פתיחה)")
    except Exception as e:
        st.error(f"שגיאה בעיבוד: {e}")