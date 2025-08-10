import streamlit as st
from supabase import create_client
import pandas as pd

# Supabase config
SUPABASE_URL = "https://qrvdfqzmaupqqjxsqezu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFydmRmcXptYXVwcXFqeHNxZXp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ1ODE5MTgsImV4cCI6MjA3MDE1NzkxOH0.c93JH5Kf3CV8uamfV3-nwbzjn5HnBEwmU7KApNcwZIU"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_companies():
    response = supabase.table("companies").select(
        "id, name, industry, city, lease_expiration, future_move, created_at"
    ).execute()
    data = response.data
    df = pd.DataFrame(data)
    return df

def main():
    st.title("Company List")

    df = load_companies()

    # Global search filter
    search_term = st.text_input("Search by company name")
    if search_term:
        df = df[df['name'].str.contains(search_term, case=False, na=False)]

    # Industry filter with 'Unknown' for missing industries
    df['industry'] = df['industry'].fillna("Unknown")
    industries = df['industry'].unique().tolist()
    selected_industry = st.selectbox("Filter by Industry", ["All"] + industries)
    if selected_industry != "All":
        if selected_industry == "Unknown":
            df = df[df['industry'] == "Unknown"]
        else:
            df = df[df['industry'] == selected_industry]

    # Convert lease_expiration column to datetime once before filters
    df['lease_expiration'] = pd.to_datetime(df['lease_expiration'], errors='coerce')

    lease_min = df['lease_expiration'].min()
    lease_max = df['lease_expiration'].max()

    lease_date_range = st.date_input("Lease Expiration between", [lease_min, lease_max])

    if lease_date_range and len(lease_date_range) == 2:
        start, end = lease_date_range
        if start is not None and end is not None:
            df = df[
                (df['lease_expiration'].isna()) |  # Include companies with no lease_expiration
                ((df['lease_expiration'] >= pd.to_datetime(start)) & (df['lease_expiration'] <= pd.to_datetime(end)))
            ]

    if df.empty:
        st.write("No companies found with the selected filters.")
    else:
        # Format date columns as string for better display
        df['lease_expiration'] = df['lease_expiration'].dt.strftime('%Y-%m-%d')
        df['future_move'] = pd.to_datetime(df['future_move'], errors='coerce').dt.strftime('%Y-%m-%d')

        # Display as interactive table
        st.dataframe(df[['name', 'industry', 'city', 'lease_expiration', 'future_move', 'created_at']])

if __name__ == "__main__":
    main()
