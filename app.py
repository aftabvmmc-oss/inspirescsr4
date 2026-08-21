import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import plotly.express as px

# --- CONFIGURATION ---
st.set_page_config(page_title="CSR4 Community Surveillance Tracker", layout="wide", initial_sidebar_state="expanded")

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
st.title("📊 CSR4 Community Surveillance Tracker")

sheet = init_connection()

# Fetch data once here so both tabs can access it without duplicate API calls
df = get_data(sheet)

tab1, tab2 = st.tabs(["📈 Live Summary & Analytics", "📝 Data Entry (Secure)"])

# ==========================================
# TAB 1: LIVE SUMMARY & ANALYTICS
# ==========================================
with tab1:
    st.header("Real-Time Analytics Dashboard")
    
    if df.empty:
        st.warning("No data found in the linked Google Sheet or connection failed.")
    else:
        st.subheader("Overview Metrics")
        
        total_structures = int(df['Houses Covered'].sum()) if 'Houses Covered' in df.columns else 0
        total_forms = int(df['Total Forms Submitted'].sum()) if 'Total Forms Submitted' in df.columns else 0
        
        total_individuals = int(df['Individuals Covered'].sum()) if 'Individuals Covered' in df.columns else 0
        ari = int(df['ARI Hospitalizations'].sum()) if 'ARI Hospitalizations' in df.columns else 0
        annual_submitted = int(df['Total ANNUAL SURVEY Forms Submitted'].sum()) if 'Total ANNUAL SURVEY Forms Submitted' in df.columns else 0
        annual_pending = int(df['Total Pending ANNUAL SURVEY Forms'].sum()) if 'Total Pending ANNUAL SURVEY Forms' in df.columns else 0
        
        # Split metrics into two vibrant rows
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        kpi_col1.metric("🏠 Structures Covered", total_structures)
        kpi_col2.metric("📝 CSR4 Forms Submitted", total_forms)
        kpi_col3.metric("👥 Individuals Covered", total_individuals)
        
        kpi_col4, kpi_col5, kpi_col6 = st.columns(3)
        kpi_col4.metric("📋 Annual Survey Forms", annual_submitted)
        kpi_col5.metric("⏳ Pending Annual Forms", annual_pending)
        kpi_col6.metric("🏥 ARI Hospitalizations", ari)
        
        st.markdown("---")

        st.subheader("📊 Village-wise Progress")
        if 'Village' in df.columns:
            village_summary = df.groupby('Village').agg({
                'Houses Covered': 'sum',
                'Total Forms Submitted': 'sum',
                'Total ANNUAL SURVEY Forms Submitted': 'sum',
                'Total Pending ANNUAL SURVEY Forms': 'sum',
                'New Locked Houses': 'sum',
                'Migrated': 'sum',
                'Individuals Covered': 'sum',
                'Died': 'sum',
                'ARI Hospitalizations': 'sum',
                'Date': 'nunique' 
            }).rename(columns={'Date': 'Person Days', 'New Locked Houses': 'Locked', 'Houses Covered': 'Structures Covered'}).reset_index()
            
            # Calculate targets and progress % 
            village_summary['Target Struct.'] = village_summary['Village'].apply(lambda x: TARGETS.get(x, {}).get('Structures', 1))
            village_summary['Struct. Prog. (%)'] = (village_summary['Structures Covered'] / village_summary['Target Struct.'] * 100).round(1).clip(upper=100.0)

            village_summary['Target Forms'] = village_summary['Village'].apply(lambda x: TARGETS.get(x, {}).get('Forms', 1))
            village_summary['Form Prog. (%)'] = (village_summary['Total Forms Submitted'] / village_summary['Target Forms'] * 100).round(1).clip(upper=100.0)
            
            # Use Target Forms as the denominator for Annual Survey
            village_summary['Annual Prog. (%)'] = (village_summary['Total ANNUAL SURVEY Forms Submitted'] / village_summary['Target Forms'] * 100).round(1).clip(upper=100.0)

            village_summary['Target Indiv.'] = village_summary['Village'].apply(lambda x: TARGETS.get(x, {}).get('Individuals', 1))
            village_summary['Indiv. Prog. (%)'] = (village_summary['Individuals Covered'] / village_summary['Target Indiv.'] * 100).round(1).clip(upper=100.0)

            st.markdown("### 📈 Village-wise Progress Breakdown")
            
            v_col1, v_col2 = st.columns(2)
            
            with v_col1:
                st.markdown("**🏠 Structures Covered**")
                st.caption("Percentage of estimated structures covered.")
                fig_struct = px.bar(village_summary, x='Village', y='Struct. Prog. (%)', text_auto='.1f', color_discrete_sequence=['#4C78A8'])
                fig_struct.update_traces(textposition='outside')
                fig_struct.update_layout(yaxis_range=[0, 115], height=300, margin=dict(t=10, b=10, l=10, r=10), xaxis_title=None, yaxis_title="%")
                st.plotly_chart(fig_struct, use_container_width=True)
                
            with v_col2:
                st.markdown("**📝 CSR4 Forms Submitted**")
                st.caption("Percentage of target CSR4 forms completed.")
                fig_form = px.bar(village_summary, x='Village', y='Form Prog. (%)', text_auto='.1f', color_discrete_sequence=['#F58518'])
                fig_form.update_traces(textposition='outside')
                fig_form.update_layout(yaxis_range=[0, 115], height=300, margin=dict(t=10, b=10, l=10, r=10), xaxis_title=None, yaxis_title="%")
                st.plotly_chart(fig_form, use_container_width=True)
                
            v_col3, v_col4 = st.columns(2)
            
            with v_col3:
                st.markdown("**📋 Annual Survey Forms**")
                st.caption("Percentage of target Annual Surveys completed.")
                fig_annual = px.bar(village_summary, x='Village', y='Annual Prog. (%)', text_auto='.1f', color_discrete_sequence=['#54A24B'])
                fig_annual.update_traces(textposition='outside')
                fig_annual.update_layout(yaxis_range=[0, 115], height=300, margin=dict(t=10, b=10, l=10, r=10), xaxis_title=None, yaxis_title="%")
                st.plotly_chart(fig_annual, use_container_width=True)
                
            with v_col4:
                st.markdown("**👥 Individuals Covered**")
                st.caption("Percentage of target individuals covered.")
                fig_indiv = px.bar(village_summary, x='Village', y='Indiv. Prog. (%)', text_auto='.1f', color_discrete_sequence=['#E45756'])
                fig_indiv.update_traces(textposition='outside')
                fig_indiv.update_layout(yaxis_range=[0, 115], height=300, margin=dict(t=10, b=10, l=10, r=10), xaxis_title=None, yaxis_title="%")
                st.plotly_chart(fig_indiv, use_container_width=True)

            st.markdown("---")
            st.subheader("🔎 Detailed Village Data Table")
            
            cols_to_show = [
                'Village', 
                'Structures Covered', 'Struct. Prog. (%)', 
                'Total Forms Submitted', 'Form Prog. (%)',
                'Total ANNUAL SURVEY Forms Submitted', 'Annual Prog. (%)',
                'Individuals Covered', 'Indiv. Prog. (%)',
                'Total Pending ANNUAL SURVEY Forms',
                'Locked', 'Migrated', 'Died', 'ARI Hospitalizations', 'Person Days'
            ]
            cols_to_show = [c for c in cols_to_show if c in village_summary.columns]
            village_summary_display = village_summary[cols_to_show]

            # Shorten column headers for better UI fit
            rename_dict = {
                'Structures Covered': 'Structs',
                'Total Forms Submitted': 'CSR4 Forms',
                'Total ANNUAL SURVEY Forms Submitted': 'Annual Forms',
                'Total Pending ANNUAL SURVEY Forms': 'Pend. Annual',
                'Individuals Covered': 'Individuals',
                'ARI Hospitalizations': 'ARI Hosp'
            }
            village_summary_display = village_summary_display.rename(columns=rename_dict)

            st.dataframe(
                village_summary_display, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Struct. Prog. (%)": st.column_config.ProgressColumn("Struct %", format="%f%%", min_value=0, max_value=100),
                    "Form Prog. (%)": st.column_config.ProgressColumn("Form %", format="%f%%", min_value=0, max_value=100),
                    "Annual Prog. (%)": st.column_config.ProgressColumn("Annual %", format="%f%%", min_value=0, max_value=100),
                    "Indiv. Prog. (%)": st.column_config.ProgressColumn("Indiv %", format="%f%%", min_value=0, max_value=100)
                }
            )

        st.markdown("---")

        st.subheader("🎯 Overall Coverage Progress")
        
        overall_df = pd.DataFrame({
            'Metric': ['Structures', 'CSR4 Forms', 'Annual Survey Forms', 'Individuals'],
            'Completed': [total_structures, total_forms, annual_submitted, total_individuals],
            'Target': [TARGETS["OVERALL"]["Structures"], TARGETS["OVERALL"]["Forms"], TARGETS["OVERALL"]["Forms"], TARGETS["OVERALL"]["Individuals"]]
        })
        # Calculate % and cap at 100 for visual sanity
        overall_df['% Completed'] = (overall_df['Completed'] / overall_df['Target'] * 100).round(1).clip(upper=100.0)
        
        fig_overall = px.bar(
            overall_df, 
            x='% Completed', 
            y='Metric', 
            orientation='h', 
            text='% Completed',
            color='Metric',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_overall.update_traces(texttemplate='%{text}%', textposition='outside')
        fig_overall.update_layout(showlegend=False, xaxis_range=[0, 115], height=300, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_overall, use_container_width=True)
            
        st.markdown("---")
        
        st.subheader("🧑‍💻 Data Collector Summary")
        if 'Data Collector' in df.columns:
            collector_summary = df.groupby('Data Collector').agg({
                'Houses Covered': 'sum',
                'Total Forms Submitted': 'sum',
                'Total ANNUAL SURVEY Forms Submitted': 'sum',
                'Migrated': 'sum',
                'Individuals Covered': 'sum',
                'Died': 'sum',
                'ARI Hospitalizations': 'sum',
                'Date': 'nunique' 
            }).rename(columns={'Date': 'Working Days'}).reset_index()
            
            collector_summary['Houses / Day'] = (collector_summary['Houses Covered'] / collector_summary['Working Days']).round(2).fillna(0)
            st.dataframe(collector_summary, use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: DATA ENTRY (LINEAR REWORK)
# ==========================================
with tab2:
    st.header("Daily Data Entry Form")
    password_input = st.text_input("Enter Password to access data entry:", type="password")
    
    if password_input not in ["admin", "rakesh"]:
        if password_input:
            st.error("Incorrect Password.")
        st.info("Please enter the password to view the data entry form.")
    else:
        if password_input == "admin":
            st.success("Access Granted. Welcome, Dr. Aftab!")
        elif password_input == "rakesh":
            st.success("Access Granted. Welcome, Mr. Rakesh!")
            
        st.markdown("---")
        
        st.subheader("📅 Recent Submissions Calendar")
        st.caption("Check this grid before entering data to avoid duplicates. Shows the villages covered by each collector over the last 10 days.")
        
        if not df.empty and 'Date' in df.columns and 'Data Collector' in df.columns:
            try:
                recent_df = df.copy()
                recent_df['Date'] = pd.to_datetime(recent_df['Date'], errors='coerce').dt.date
                recent_df = recent_df.dropna(subset=['Date'])
                
                # Create pivot table (Dates as rows, Collectors as columns)
                pivot_df = recent_df.pivot_table(
                    index='Date', 
                    columns='Data Collector', 
                    values='Village', 
                    aggfunc=lambda x: '✅ ' + ', '.join(set(x.astype(str)))
                )
                
                # Ensure all defined collectors appear as columns even if they have no entries
                for col in DATA_COLLECTORS:
                    if col not in pivot_df.columns:
                        pivot_df[col] = '❌ Missing'
                        
                # Fill blank cells with missing emoji and sort by newest dates
                pivot_df = pivot_df.fillna('❌ Missing').sort_index(ascending=False).head(10)
                pivot_df.index = pivot_df.index.astype(str)
                
                st.dataframe(pivot_df, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not load calendar view: {e}")
        else:
            st.info("No historical data available to show.")
            
        st.markdown("---")
        
        with st.form("data_entry_form", clear_on_submit=True):
            
            st.markdown("### 👤 Meta Data")
            entry_date = st.date_input("Date", datetime.date.today())
            
            # Use horizontal radio buttons to keep it readable but linear
            data_collector = st.radio("Data Collector", DATA_COLLECTORS, horizontal=True)
            village = st.radio("Village", VILLAGES, horizontal=True)
                
            st.markdown("### 🏠 Coverage & Houses")
            
            # From / To House numbers side by side in two columns
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                from_house = st.number_input("From House No.", min_value=0, step=1)
            with col_h2:
                to_house = st.number_input("To House No.", min_value=0, step=1)
                
            # Locked Houses Covered and New Locked houses side by side
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                locked_houses_covered = st.number_input("Locked Houses Covered", min_value=0, step=1)
            with col_l2:
                new_locked_houses = st.number_input("New Locked Houses", min_value=0, step=1)
                
            migrated = st.number_input("Migrated", min_value=0, step=1)
                
            st.markdown("### 👥 Individuals & Health Metrics")
            total_forms_submitted = st.number_input("Total Forms Submitted (CSR4)", min_value=0, step=1)
            individuals_covered = st.number_input("Individuals Covered", min_value=0, step=1)
            died = st.number_input("Died", min_value=0, step=1)
            ari_hosp = st.number_input("ARI Hospitalizations", min_value=0, step=1)
            
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
