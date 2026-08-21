import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="CSR3 Community Surveillance Tracker", layout="wide", initial_sidebar_state="expanded")

# --- CONSTANTS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1LwUtBMh_M58Y_SxWXfvwGvBWkAInY_rMGFLMpeRY9-M/edit?usp=sharing"
DATA_COLLECTORS = ["Deendayal", "Sachin", "Pradeep", "Rajkumar"] 
VILLAGES = ["Sunped", "Sagarpur", "Prahladpur", "Deegh", "Pyala", "Khandawali"] 

# --- GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def init_connection():
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=scopes
            )
        else:
            st.error("Google Cloud credentials not found in secrets.")
            st.stop()

        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        return sheet
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {e}")
        st.stop()

# --- DATA FETCHING ---
def get_data(sheet):
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        numeric_cols = ['From House No.', 'To House No.', 'Locked Houses Covered', 'Houses Covered', 
                        'Total Forms Submitted', 'New Locked Houses', 'Migrated', 'Individuals Covered', 
                        'Died', 'ARI Hospitalizations', 'Total ANNUAL SURVEY Forms Submitted', 'Total Pending ANNUAL SURVEY Forms']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# --- MAIN APP LAYOUT ---
st.title("📊 CSR3 Community Surveillance Tracker")

sheet = init_connection()
tab1, tab2 = st.tabs(["📈 Live Summary & Analytics", "📝 Data Entry (Secure)"])

# ==========================================
# TAB 1: LIVE SUMMARY & ANALYTICS
# ==========================================
with tab1:
    st.header("Real-Time Analytics Dashboard")
    df = get_data(sheet)
    
    if df.empty:
        st.warning("No data found in the linked Google Sheet or connection failed.")
    else:
        st.subheader("Overview Metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Structures Covered", int(df['Houses Covered'].sum()) if 'Houses Covered' in df.columns else 0)
        col2.metric("Total CSR4 Forms Submitted", int(df['Total Forms Submitted'].sum()) if 'Total Forms Submitted' in df.columns else 0)
        col3.metric("Total Individuals Covered", int(df['Individuals Covered'].sum()) if 'Individuals Covered' in df.columns else 0)
        col4.metric("Total ARI Hospitalizations", int(df['ARI Hospitalizations'].sum()) if 'ARI Hospitalizations' in df.columns else 0)

        st.subheader("Annual Survey Progress")
        as_col1, as_col2 = st.columns(2)
        annual_submitted = int(df['Total ANNUAL SURVEY Forms Submitted'].sum()) if 'Total ANNUAL SURVEY Forms Submitted' in df.columns else 0
        annual_pending = int(df['Total Pending ANNUAL SURVEY Forms'].sum()) if 'Total Pending ANNUAL SURVEY Forms' in df.columns else 0
        as_col1.metric("Total ANNUAL SURVEY Forms Submitted", annual_submitted)
        as_col2.metric("Total Pending ANNUAL SURVEY Forms", annual_pending)

        st.markdown("---")
        
        st.subheader("Data Collector Summary")
        if 'Data Collector' in df.columns:
            collector_summary = df.groupby('Data Collector').agg({
                'Houses Covered': 'sum',
                'Total Forms Submitted': 'sum',
                'Migrated': 'sum',
                'Individuals Covered': 'sum',
                'Died': 'sum',
                'ARI Hospitalizations': 'sum',
                'Date': 'nunique' 
            }).rename(columns={'Date': 'Working Days'}).reset_index()
            
            collector_summary['Houses / Day'] = (collector_summary['Houses Covered'] / collector_summary['Working Days']).round(2).fillna(0)
            st.dataframe(collector_summary, use_container_width=True)
            
        st.subheader("Village-wise Summary")
        if 'Village' in df.columns:
            village_summary = df.groupby('Village').agg({
                'Houses Covered': 'sum',
                'Total Forms Submitted': 'sum',
                'New Locked Houses': 'sum',
                'Migrated': 'sum',
                'Individuals Covered': 'sum',
                'Died': 'sum',
                'ARI Hospitalizations': 'sum',
                'Date': 'nunique' 
            }).rename(columns={'Date': 'Person Days', 'New Locked Houses': 'Locked', 'Houses Covered': 'Structures Covered'}).reset_index()
            st.dataframe(village_summary, use_container_width=True)

# ==========================================
# TAB 2: DATA ENTRY (LINEAR REWORK)
# ==========================================
with tab2:
    st.header("Daily Data Entry Form")
    password_input = st.text_input("Enter Admin Password to access data entry:", type="password")
    
    if password_input != "admin":
        if password_input:
            st.error("Incorrect Password.")
        st.info("Please enter the password to view the data entry form.")
    else:
        st.success("Access Granted.")
        st.markdown("---")
        
        # clear_on_submit=True resets the form automatically after submission
        with st.form("data_entry_form", clear_on_submit=True):
            
            st.subheader("📍 General Information")
            entry_date = st.date_input("Date of Survey", datetime.date.today())
            
            # Radio buttons instead of dropdowns (horizontal for better spacing)
            data_collector = st.radio("Data Collector", DATA_COLLECTORS, horizontal=True)
            village = st.radio("Village", VILLAGES, horizontal=True)
                
            st.markdown("---")
            st.subheader("🏠 Logistical Coverage (CSR4)")
            
            # House numbers in two columns
            col_a, col_b = st.columns(2)
            with col_a:
                from_house = st.number_input("From House No.", min_value=0, step=1)
            with col_b:
                to_house = st.number_input("To House No.", min_value=0, step=1)
            
            # Locked houses in two columns
            col_c, col_d = st.columns(2)
            with col_c:
                locked_houses_covered = st.number_input("Locked Houses Covered", min_value=0, step=1)
            with col_d:
                new_locked_houses = st.number_input("New Locked Houses", min_value=0, step=1)
                
            # Remaining fields are linear (single column)
            migrated = st.number_input("Migrated Families", min_value=0, step=1)
                
            st.markdown("---")
            st.subheader("⚕️ Health & Demographics (CSR4)")
            total_forms_submitted = st.number_input("Total Forms Submitted", min_value=0, step=1)
            individuals_covered = st.number_input("Individuals Covered", min_value=0, step=1)
            ari_hosp = st.number_input("ARI Hospitalizations", min_value=0, step=1)
            died = st.number_input("Deaths (Died)", min_value=0, step=1)

            st.markdown("---")
            st.subheader("📋 Annual Survey Status")
            annual_forms_submitted = st.number_input("Total ANNUAL SURVEY Forms Submitted", min_value=0, step=1)
            annual_forms_pending = st.number_input("Total Pending ANNUAL SURVEY Forms", min_value=0, step=1)
                
            submit_button = st.form_submit_button("Submit Daily Data", type="primary")
            
            # Processing on submit
            if submit_button:
                if to_house >= from_house:
                     calculated_houses_covered = (to_house - from_house + 1) + locked_houses_covered
                else:
                     calculated_houses_covered = 0
                     
                new_row = [
                    entry_date.strftime("%Y-%m-%d"), data_collector, village, from_house, to_house,
                    locked_houses_covered, calculated_houses_covered, total_forms_submitted,
                    new_locked_houses, migrated, individuals_covered, died, ari_hosp,
                    annual_forms_submitted, annual_forms_pending
                ]
                
                try:
                    sheet.append_row(new_row)
                    st.success("✅ Data submitted successfully! The form has been cleared for your next entry.")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Failed to submit data: {e}")
