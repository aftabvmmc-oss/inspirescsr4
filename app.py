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

# TARGET DENOMINATORS
TARGETS = {
    "Sunped": {"Structures": 446, "Forms": 746, "Individuals": 1751},
    "Sagarpur": {"Structures": 479, "Forms": 848, "Individuals": 1975},
    "Prahladpur": {"Structures": 413, "Forms": 754, "Individuals": 1704},
    "Deegh": {"Structures": 637, "Forms": 1179, "Individuals": 2664},
    "Pyala": {"Structures": 747, "Forms": 1382, "Individuals": 3200},
    "Khandawali": {"Structures": 568, "Forms": 1250, "Individuals": 3104},
    "OVERALL": {"Structures": 3290, "Forms": 6159, "Individuals": 14398}
}

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
        
        total_structures = int(df['Houses Covered'].sum()) if 'Houses Covered' in df.columns else 0
        total_forms = int(df['Total Forms Submitted'].sum()) if 'Total Forms Submitted' in df.columns else 0
        total_individuals = int(df['Individuals Covered'].sum()) if 'Individuals Covered' in df.columns else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Structures Covered", total_structures)
        col2.metric("Total CSR4 Forms Submitted", total_forms)
        col3.metric("Total Individuals Covered", total_individuals)
        col4.metric("Total ARI Hospitalizations", int(df['ARI Hospitalizations'].sum()) if 'ARI Hospitalizations' in df.columns else 0)

        st.subheader("🎯 Overall Coverage Progress (vs Targets)")
        prog_col1, prog_col2, prog_col3 = st.columns(3)
        
        with prog_col1:
            struct_pct = min(total_structures / TARGETS["OVERALL"]["Structures"], 1.0)
            st.markdown(f"**Structures:** {total_structures} / {TARGETS['OVERALL']['Structures']} ({struct_pct*100:.1f}%)")
            st.progress(struct_pct)
            
        with prog_col2:
            forms_pct = min(total_forms / TARGETS["OVERALL"]["Forms"], 1.0)
            st.markdown(f"**Forms:** {total_forms} / {TARGETS['OVERALL']['Forms']} ({forms_pct*100:.1f}%)")
            st.progress(forms_pct)
            
        with prog_col3:
            ind_pct = min(total_individuals / TARGETS["OVERALL"]["Individuals"], 1.0)
            st.markdown(f"**Individuals:** {total_individuals} / {TARGETS['OVERALL']['Individuals']} ({ind_pct*100:.1f}%)")
            st.progress(ind_pct)
            
        st.markdown("---")

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
            st.dataframe(collector_summary, use_container_width=True, hide_index=True)
            
        st.subheader("Village-wise Summary & Progress")
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
            
            # Calculate targets and progress % for the dataframe
            village_summary['Target Structures'] = village_summary['Village'].apply(lambda x: TARGETS.get(x, {}).get('Structures', 1))
            village_summary['Struct. Prog. (%)'] = (village_summary['Structures Covered'] / village_summary['Target Structures'] * 100).round(1).clip(upper=100.0)

            village_summary['Target Forms'] = village_summary['Village'].apply(lambda x: TARGETS.get(x, {}).get('Forms', 1))
            village_summary['Form Prog. (%)'] = (village_summary['Total Forms Submitted'] / village_summary['Target Forms'] * 100).round(1).clip(upper=100.0)

            village_summary['Target Indiv.'] = village_summary['Village'].apply(lambda x: TARGETS.get(x, {}).get('Individuals', 1))
            village_summary['Indiv. Prog. (%)'] = (village_summary['Individuals Covered'] / village_summary['Target Indiv.'] * 100).round(1).clip(upper=100.0)

            # Reorder columns cleanly
            cols_to_show = [
                'Village', 
                'Structures Covered', 'Target Structures', 'Struct. Prog. (%)', 
                'Total Forms Submitted', 'Target Forms', 'Form Prog. (%)',
                'Individuals Covered', 'Target Indiv.', 'Indiv. Prog. (%)',
                'Locked', 'Migrated', 'Died', 'ARI Hospitalizations', 'Person Days'
            ]
            cols_to_show = [c for c in cols_to_show if c in village_summary.columns]
            village_summary = village_summary[cols_to_show]

            # Display dataframe with configured column progress bars
            st.dataframe(
                village_summary, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Struct. Prog. (%)": st.column_config.ProgressColumn(
                        "Structure %",
                        help="Percentage of target structures covered",
                        format="%f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "Form Prog. (%)": st.column_config.ProgressColumn(
                        "Form %",
                        help="Percentage of target forms submitted",
                        format="%f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "Indiv. Prog. (%)": st.column_config.ProgressColumn(
                        "Individual %",
                        help="Percentage of target individuals covered",
                        format="%f%%",
                        min_value=0,
                        max_value=100,
                    )
                }
            )

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
