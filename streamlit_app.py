import streamlit as st
from supabase import create_client, Client
import uuid
import pandas as pd

# --- Supabase config ---
SUPABASE_URL = "https://qrvdfqzmaupqqjxsqezu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFydmRmcXptYXVwcXFqeHNxZXp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ1ODE5MTgsImV4cCI6MjA3MDE1NzkxOH0.c93JH5Kf3CV8uamfV3-nwbzjn5HnBEwmU7KApNcwZIU"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def load_companies():
    response = supabase.table("companies").select(
        "id, name, industry, city, source, sf_occupied, lease_expiration, future_move, created_at"
    ).execute()
    return pd.DataFrame(response.data)

def company_list_view():
    st.set_page_config(page_title="Company List", layout="wide")
    st.title("Company List")

    df = load_companies()

    # Global search filter
    search_term = st.text_input("Search by company name")
    if search_term:
        df = df[df['name'].str.contains(search_term, case=False, na=False)]

    # Industry filter
    df['industry'] = df['industry'].fillna("Unknown")
    industries = df['industry'].unique().tolist()
    selected_industry = st.selectbox("Filter by Industry", ["All"] + industries)
    if selected_industry != "All":
        df = df[df['industry'] == selected_industry]

    # Source filter
    df['source'] = df['source'].fillna("Unknown")
    source = df['source'].unique().tolist()
    selected_source = st.selectbox("Filter by Source", ["All"] + source)
    if selected_source != "All":
        df = df[df['source'] == selected_source]

    # Lease expiration filter
    df['lease_expiration'] = pd.to_datetime(df['lease_expiration'], errors='coerce')

# Handle case when all values are NaT
    if df['lease_expiration'].notna().any():
        lease_min = df['lease_expiration'].min()
        lease_max = df['lease_expiration'].max()
    else:
        # Fallback default range
        lease_min = pd.Timestamp("2000-01-01")
        lease_max = pd.Timestamp.today()

    lease_date_range = st.date_input(
    "Lease Expiration between",
    [lease_min, lease_max]
    )

    if df.empty:
        st.warning("No companies found with the selected filters.")
    else:
        # Format clickable company names
        df['name'] = df.apply(
            lambda row: f'<a href="/company_detail?company_id={row["id"]}">{row["name"]}</a>',
            axis=1
        )

        # Format date columns
        df['lease_expiration'] = df['lease_expiration'].dt.strftime('%Y-%m-%d')
        df['future_move'] = pd.to_datetime(df['future_move'], errors='coerce').dt.strftime('%Y-%m-%d')

        # Show table with clickable links
        st.markdown(
            df[['name', 'industry', 'city', 'source', 'lease_expiration', 'future_move', 'sf_occupied', 'created_at']]
            .to_html(escape=False, index=False),
            unsafe_allow_html=True
        )

def company_detail_view(company_id):
    st.title("🔍 Company Details")

    if not is_valid_uuid(company_id):
        st.error("❌ Invalid company ID")
        return

    # Fetch company
    company_response = supabase.table("companies").select("*").eq("id", company_id).single().execute()
    if company_response.data is None:
        st.error("❌ Company not found.")
        return

    company = company_response.data

    # Show Back button
    if st.button("⬅️ Back to Company List"):
        st.query_params.clear()  # clear query params
        st.rerun()

    st.subheader("Company Info")
    with st.form("edit_company_form"):
        name = st.text_input("Name", value=company.get("name", ""))
        website = st.text_input("Website", value=company.get("website", ""))
        industry = st.text_input("Industry", value=company.get("industry", ""))
        size = st.text_input("Size", value=company.get("size", ""))

        st.markdown("---")  # separator for clarity

        col1, col2, col3 = st.columns(3)

        with col1:
            source = st.text_input("Source", value=company.get("source", ""))
            location = st.text_input("Location", value=company.get("location", ""))
            city = st.text_input("City", value=company.get("city", ""))
            state = st.text_input("State", value=company.get("state", ""))

        with col2:
            zip_code = st.text_input("Zip", value=company.get("zip", ""))
            lease_expiration_val = company.get("lease_expiration")
            lease_expiration = st.date_input(
                "Lease Expiration", 
                value=pd.to_datetime(lease_expiration_val).date() if lease_expiration_val else None
            )
            future_move = st.text_input("Future Move", value=company.get("future_move", ""))
            landlord = st.text_input("Landlord", value=company.get("landlord", ""))

        with col3:
            landlord_rep = st.text_input("Landlord Rep", value=company.get("landlord_rep", ""))
            floor = st.text_input("Floor", value=company.get("floor", ""))
            space_use = st.text_input("Space Use", value=company.get("space_use", ""))
            sf_occupied = st.text_input("SF Occupied", value=company.get("sf_occupied", ""))

        st.markdown("---")
        notes = st.text_area("Notes", value=company.get("notes", ""))

        submitted = st.form_submit_button("Save Changes")
        if submitted:
            update_payload = {
                "name": name,
                "website": website,
                "industry": industry,
                "size": size,
                "source": source,
                "location": location,
                "city": city,
                "state": state,
                "zip": zip_code,
                "lease_expiration": lease_expiration.isoformat() if lease_expiration else None,
                "future_move": future_move,
                "landlord": landlord,
                "landlord_rep": landlord_rep,
                "floor": floor,
                "space_use": space_use,
                "sf_occupied": sf_occupied,
                "notes": notes
            }
            update_response = supabase.table("companies").update(update_payload).eq("id", company_id).execute()

            if getattr(update_response, "error", None):
                st.error(f"❌ Update failed: {update_response.data}")
            else:
                st.success("✅ Company info updated.")

    # --- Contacts ---
    st.markdown("---")
    st.subheader("📇 Contacts Overview")

    # Fetch users for assignment/updated_by
    users_response = supabase.table("users").select("id, name").execute()
    reps_list = users_response.data or []
    rep_name_to_id = {u["name"]: u["id"] for u in reps_list}

    # Fetch contacts
    contacts_response = supabase.table("contacts").select("*").eq("company_id", company_id).execute()
    contacts = contacts_response.data or []

    if not contacts:
        st.write("No contacts found.")
    else:
        df_contacts = pd.DataFrame(contacts)

        # Status color helper
        def status_color(status):
            colors = {
                "bounced": "background-color: #f8d7da; color: #721c24",
                "replied": "background-color: #d1ecf1; color: #0c5460",
                "interested": "background-color: #d4edda; color: #155724",
                "not interested": "background-color: #f8d7da; color: #721c24",
                "needs follow-up": "background-color: #fff3cd; color: #856404",
                "no response": "background-color: #fff3cd; color: #856404"
            }
            return colors.get(status, "")

        def style_status(row):
            return [status_color(row['contact_status']) if col == 'contact_status' else '' for col in row.index]

        display_cols = ['full_name', 'email', 'phone', 'contact_status']
        st.dataframe(df_contacts[display_cols].style.apply(style_status, axis=1), use_container_width=True)

        st.markdown("---")
        st.subheader("✏️ Edit Contacts")

        quality_options = ["", "good", "bad", "unknown"]
        call_outcomes = ["", "connected", "voicemail", "no answer", "left message"]
        outreach_options = ["email", "linkedin", "phone", "dm", "other"]

        for contact in contacts:
            with st.expander(f"Edit Contact: {contact.get('full_name', 'N/A')}"):
                with st.form(f"contact_form_{contact['id']}"):

            # --- 3 column layout for better grouping ---
                    col1, col2, col3 = st.columns(3)

            # Column 1 - Basic Info
            with col1:
                full_name = st.text_input("Full Name", value=contact.get("full_name", ""))
                email = st.text_input("Email", value=contact.get("email", ""))
                phone = st.text_input("Phone", value=contact.get("phone", ""))
                linkedin = st.text_input("LinkedIn", value=contact.get("linkedin", ""))

            # Column 2 - Status & Quality
            with col2:
                contact_status = st.selectbox(
                    "Contact Status",
                    ["", "bounced", "replied", "interested", "not interested", "needs follow-up", "no response"],
                    index=(
                        ["", "bounced", "replied", "interested", "not interested", "needs follow-up", "no response"]
                        .index(contact.get("contact_status", ""))
                        if contact.get("contact_status", "") in 
                        ["", "bounced", "replied", "interested", "not interested", "needs follow-up", "no response"] 
                        else 0
                    )
                )
                email_quality = st.selectbox(
                    "Email Quality",
                    quality_options,
                    index=quality_options.index(contact.get("email_quality", "")) if contact.get("email_quality") in quality_options else 0
                )
                phone_quality = st.selectbox(
                    "Phone Quality",
                    quality_options,
                    index=quality_options.index(contact.get("phone_quality", "")) if contact.get("phone_quality") in quality_options else 0
                )
                last_call_outcome = st.selectbox(
                    "Last Call Outcome",
                    call_outcomes,
                    index=call_outcomes.index(contact.get("last_call_outcome", "")) if contact.get("last_call_outcome") in call_outcomes else 0
                )

            # Column 3 - Scheduling & Ownership
            with col3:
                first_contacted_date = st.date_input(
                    "First Contacted Date",
                    value=pd.to_datetime(contact.get("first_contacted_date")).date() if contact.get("first_contacted_date") else None
                )
                next_follow_up_date = st.date_input(
                    "Next Follow-Up Date",
                    value=pd.to_datetime(contact.get("next_follow_up_date")).date() if contact.get("next_follow_up_date") else None
                )
                outreach_channels = st.multiselect(
                    "Outreach Channels",
                    outreach_options,
                    default=contact.get("outreach_channels") or []
                )
                updated_by_name = st.selectbox(
                    "Updated By",
                    ["", "Corlene", "Jane"],
                    index=(["", "Corlene", "Jane"]).index(
                        contact.get("updated_by_name", "") if contact.get("updated_by_name") in ["Corlene", "Jane"] else ""
                    )
                )

            # --- Notes section below for full width ---
                notes = st.text_area("Notes", value=contact.get("notes", ""), height=150)

                submitted = st.form_submit_button("💾 Save Contact")
                if submitted:
                        update_payload = {
                            "full_name": full_name,
                            "email": email,
                            "phone": phone,
                            "linkedin": linkedin,
                            "first_contacted_date": first_contacted_date.isoformat() if first_contacted_date else None,
                            "next_follow_up_date": next_follow_up_date.isoformat() if next_follow_up_date else None,
                            "contact_status": contact_status,
                            "email_quality": email_quality,
                            "phone_quality": phone_quality,
                            "last_call_outcome": last_call_outcome,
                            "outreach_channels": outreach_channels,
                            "notes": notes,
                            "updated_by": updated_by_name if updated_by_name else None
                        }
                        update_response = supabase.table("contacts").update(update_payload).eq("id", contact["id"]).execute()
                        if hasattr(update_response, "error") and update_response.error:
                            st.error(f"❌ Update failed: {update_response.error.message}")
                        else:
                            st.success("✅ Contact updated.")
                            st.rerun()

    # --- Add New Contact form ---
    st.markdown("---")
    st.subheader("➕ Add New Contact")

    quality_options = ["", "good", "bad", "unknown"]
    call_outcomes = ["", "connected", "voicemail", "no answer", "left message"]
    outreach_options = ["email", "linkedin", "phone", "dm", "other"]

    with st.form("add_contact_form"):
        col1, col2, col3 = st.columns(3)

    # Column 1 - Basic Info
        with col1:
            new_full_name = st.text_input("Full Name")
            new_email = st.text_input("Email")
            new_phone = st.text_input("Phone")
            new_linkedin = st.text_input("LinkedIn")

    # Column 2 - Status & Quality
        with col2:
            new_contact_status = st.selectbox(
                "Contact Status",
                ["", "bounced", "replied", "interested", "not interested", "needs follow-up", "no response"],
                index=0
            )
            new_email_quality = st.selectbox("Email Quality", quality_options, index=0)
            new_phone_quality = st.selectbox("Phone Quality", quality_options, index=0)
            new_last_call_outcome = st.selectbox("Last Call Outcome", call_outcomes, index=0)

    # Column 3 - Scheduling & Ownership
        with col3:
            new_next_follow_up_date = st.date_input("Next Follow-Up Date")
            new_outreach_channels = st.multiselect(
                "Outreach Channels",
                outreach_options
            )
            new_updated_by = st.selectbox(
            "Updated By",
            ["", "Corlene", "Jane"],
            index=0
            )

    # Full-width Notes
        new_notes = st.text_area("Notes", height=150)

    # Submit button
        submitted_new = st.form_submit_button("➕ Add Contact")

        if submitted_new:
            insert_payload = {
                "full_name": new_full_name,
                "email": new_email,
                "phone": new_phone,
                "linkedin": new_linkedin,
                "next_follow_up_date": new_next_follow_up_date.isoformat() if new_next_follow_up_date else None,
                "contact_status": new_contact_status,
                "email_quality": new_email_quality,
                "phone_quality": new_phone_quality,
                "last_call_outcome": new_last_call_outcome,
                "outreach_channels": new_outreach_channels,
                "notes": new_notes,
                "updated_by": new_updated_by if new_updated_by else None,
                "company_id": company_id
            }
            insert_response = supabase.table("contacts").insert(insert_payload).execute()
            if hasattr(insert_response, "error") and insert_response.error:
                st.error(f"❌ Add failed: {insert_response.error.message}")
            else:
                st.success("✅ Contact added.")
                st.rerun()

def main():
    st.set_page_config(page_title="Lead Management System", layout="wide")

    # st.query_params now returns a dict-like object
    query_params = st.query_params
    company_id_raw = query_params.get("company_id", None)

    if company_id_raw:
        # If company_id is passed as a list/tuple, get the first element
        if isinstance(company_id_raw, (list, tuple)):
            company_id_raw = company_id_raw[0]
        company_detail_view(company_id_raw)
    else:
        company_list_view()

if __name__ == "__main__":
    main()

