import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- CONFIGURATION & STYLING ---
# Force Light Mode and set page layout
st.set_page_config(page_title="CSR3 Community Surveillance Tracker", layout="wide", initial_sidebar_state="expanded")

# Inject CSS to force a light background
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFFFFF;
        color: #000000;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- CONSTANTS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1LwUtBMh_M58Y_SxWXfvwGvBWkAInY_rMGFLMpeRY9-M/edit?usp=sharing"
DATA_COLLECTORS = ["Deendayal", "Sachin", "Pradeep", "Rajkumar"] # Add or remove names here
VILLAGES = ["Sunped", "Sagarpur", "Prahladpur", "Deegh", "Pyala", "Khandawali"] # Add or remove villages here

# --- GOOGLE SHEETS CONNECTION ---
@st.cache_resource
def init_connection():
    """
    Initializes the Google Sheets connection.
    Requires you to set up Google Service Account credentials.
    In Streamlit Cloud, store the JSON contents in st.secrets["gcp_service_account"].
    """
    try:
        # Define the scope
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Load credentials from Streamlit Secrets
        # Make sure you have set up your secrets in your hosting platform
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=scopes
            )
        else:
            st.error("Google Cloud credentials not found in secrets. Please configure 'gcp_service_account'.")
            st.stop()

        client = gspread.authorize(creds)
        
        # Open the specific sheet by URL
        sheet = client.open_by_url(SHEET_URL).sheet1
        return sheet
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {e}")
        st.stop()

# --- DATA FETCHING ---
def get_data(sheet):
    """Fetches data from Google Sheets and returns a Pandas DataFrame."""
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Data type conversions for calculations
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

# Initialize connection
sheet = init_connection()

# Define Tabs (Summary appears first as requested)
tab1, tab2 = st.tabs(["📈 Live Summary & Analytics", "📝 Data Entry (Secure)"])

# ==========================================
# TAB 1: LIVE SUMMARY & ANALYTICS (Public)
# ==========================================
with tab1:
    st.header("Real-Time Analytics Dashboard")
    
    # Fetch latest data
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

        # Separate Section for Annual Survey Metrics
        st.subheader("Annual Survey Progress")
        as_col1, as_col2 = st.columns(2)
        annual_submitted = int(df['Total ANNUAL SURVEY Forms Submitted'].sum()) if 'Total ANNUAL SURVEY Forms Submitted' in df.columns else 0
        annual_pending = int(df['Total Pending ANNUAL SURVEY Forms'].sum()) if 'Total Pending ANNUAL SURVEY Forms' in df.columns else 0
        as_col1.metric("Total ANNUAL SURVEY Forms Submitted", annual_submitted)
        as_col2.metric("Total Pending ANNUAL SURVEY Forms", annual_pending)

        st.markdown("---")
        
        st.subheader("Data Collector Summary")
        if 'Data Collector' in df.columns:
             # Group by Data Collector
            collector_summary = df.groupby('Data Collector').agg({
                'Houses Covered': 'sum',
                'Total Forms Submitted': 'sum',
                'Migrated': 'sum',
                'Individuals Covered': 'sum',
                'Died': 'sum',
                'ARI Hospitalizations': 'sum',
                'Date': 'nunique' # Approximate working days
            }).rename(columns={'Date': 'Working Days'}).reset_index()
            
            # Calculate Derived Metrics safely
            collector_summary['Houses / Day'] = (collector_summary['Houses Covered'] / collector_summary['Working Days']).round(2).fillna(0)
            
            st.dataframe(collector_summary, use_container_width=True)
            
        st.subheader("Village-wise Summary")
        if 'Village' in df.columns:
            # Group by Village
            village_summary = df.groupby('Village').agg({
                'Houses Covered': 'sum',
                'Total Forms Submitted': 'sum',
                'New Locked Houses': 'sum',
                'Migrated': 'sum',
                'Individuals Covered': 'sum',
                'Died': 'sum',
                'ARI Hospitalizations': 'sum',
                'Date': 'nunique' # Approximate Person Days
            }).rename(columns={'Date': 'Person Days', 'New Locked Houses': 'Locked', 'Houses Covered': 'Structures Covered'}).reset_index()
            
            st.dataframe(village_summary, use_container_width=True)

# ==========================================
# TAB 2: DATA ENTRY (Password Protected)
# ==========================================
with tab2:
    st.header("Daily Data Entry Form")
    
    # Simple Authentication
    password_input = st.text_input("Enter Admin Password to access data entry:", type="password")
    
    if password_input != "admin":
        if password_input:
            st.error("Incorrect Password.")
        st.info("Please enter the password to view the data entry form.")
    else:
        st.success("Access Granted.")
        st.markdown("---")
        
        with st.form("data_entry_form"):
            st.subheader("General Information")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                entry_date = st.date_input("Date", datetime.date.today())
            with col2:
                data_collector = st.selectbox("Data Collector", DATA_COLLECTORS)
            with col3:
                village = st.selectbox("Village", VILLAGES)
                
            st.markdown("---")
            st.subheader("CSR4 House and Form Data")
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                from_house = st.number_input("From House No.", min_value=0, value=0)
            with col_b:
                to_house = st.number_input("To House No.", min_value=0, value=0)
            with col_c:
                locked_houses_covered = st.number_input("Locked Houses Covered", min_value=0, value=0)
            
            col_d, col_e, col_f = st.columns(3)
            
            with col_d:
                 total_forms_submitted = st.number_input("Total Forms Submitted", min_value=0, value=0)
            with col_e:
                new_locked_houses = st.number_input("New Locked Houses", min_value=0, value=0)
            with col_f:
                migrated = st.number_input("Migrated", min_value=0, value=0)
                
            st.markdown("---")
            st.subheader("Population and Health Metrics")
            col_g, col_h, col_i = st.columns(3)
            
            with col_g:
                individuals_covered = st.number_input("Individuals Covered", min_value=0, value=0)
            with col_h:
                died = st.number_input("Died", min_value=0, value=0)
            with col_i:
                 ari_hosp = st.number_input("ARI Hospitalizations", min_value=0, value=0)

            st.markdown("---")
            st.subheader("📋 Annual Survey Status")
            st.info("Note: These are distinct from the daily CSR4 forms.")
            col_as1, col_as2 = st.columns(2)
            with col_as1:
                annual_forms_submitted = st.number_input("Total No. of ANNUAL SURVEY forms submitted", min_value=0, value=0)
            with col_as2:
                annual_forms_pending = st.number_input("Total Pending ANNUAL SURVEY forms", min_value=0, value=0)
                
            submit_button = st.form_submit_button("Submit Daily Data")
            
            if submit_button:
                # Background Calculation (Column G equivalent)
                # Calculates Houses Covered: (To - From + 1) + Locked Houses Covered
                # Includes safety check if To House is less than From House
                if to_house >= from_house:
                     calculated_houses_covered = (to_house - from_house + 1) + locked_houses_covered
                else:
                     calculated_houses_covered = 0
                     
                new_row = [
                    entry_date.strftime("%Y-%m-%d"),
                    data_collector,
                    village,
                    from_house,
                    to_house,
                    locked_houses_covered,
                    calculated_houses_covered, # Calculated field
                    total_forms_submitted,
                    new_locked_houses,
                    migrated,
                    individuals_covered,
                    died,
                    ari_hosp,
                    annual_forms_submitted, # New Column
                    annual_forms_pending    # New Column
                ]
                
                try:
                    # Append row to Google Sheet
                    sheet.append_row(new_row)
                    st.success("✅ Data submitted successfully! The summary tab has been updated.")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Failed to submit data: {e}")