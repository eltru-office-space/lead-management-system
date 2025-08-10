import streamlit as st
from supabase import create_client, Client
import uuid
import pandas as pd

# --- Supabase config ---
SUPABASE_URL = "https://qrvdfqzmaupqqjxsqezu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFydmRmcXptYXVwcXFqeHNxZXp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ1ODE5MTgsImV4cCI6MjA3MDE1NzkxOH0.c93JH5Kf3CV8uamfV3-nwbzjn5HnBEwmU7KApNcwZIU"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Page setup ---
st.set_page_config(page_title="Company Detail", layout="wide")
st.title("🔍 Company Details")

# --- Parse query param ---
company_id_raw = "1c03276e-4bbd-48ba-bcae-86a90a0c3655"
st.markdown(f"**Raw Query Param:** `{company_id_raw}`")

# --- Validate company_id as UUID ---
def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

if not company_id_raw or not is_valid_uuid(company_id_raw):
    st.error("❌ No valid company ID provided.")
    st.stop()

# --- Fetch company ---
company_response = supabase.table("companies").select("*").eq("id", company_id_raw).single().execute()

if company_response.data is None:
    st.error("❌ Company not found.")
    st.stop()

company = company_response.data

# --- Display/Edit company form ---
st.subheader("Company Info")
with st.form("edit_company_form"):
    # First row: main info in one column
    name = st.text_input("Name", value=company.get("name", ""))
    website = st.text_input("Website", value=company.get("website", ""))
    industry = st.text_input("Industry", value=company.get("industry", ""))
    size = st.text_input("Size", value=company.get("size", ""))

    st.markdown("---")  # separator for clarity

    # Create 3 columns for additional fields
    col1, col2, col3 = st.columns(3)

    with col1:
        source = st.text_input("Source", value=company.get("source", ""))
        location = st.text_input("Location", value=company.get("location", ""))
        city = st.text_input("City", value=company.get("city", ""))
        state = st.text_input("State", value=company.get("state", ""))

    with col2:
        zip_code = st.text_input("Zip", value=company.get("zip", ""))
        lease_expiration = st.date_input(
            "Lease Expiration", 
            value=company.get("lease_expiration") if company.get("lease_expiration") else None
        )
        future_move = st.text_input("Future Move", value=company.get("future_move", ""))
        landlord = st.text_input("Landlord", value=company.get("landlord", ""))

    with col3:
        landlord_rep = st.text_input("Landlord Rep", value=company.get("landlord_rep", ""))
        floor = st.text_input("Floor", value=company.get("floor", ""))
        space_use = st.text_input("Space Use", value=company.get("space_use", ""))
        sf_occupied = st.text_input("SF Occupied", value=company.get("sf_occupied", ""))

    st.markdown("---")  # separator before notes
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
        update_response = supabase.table("companies").update(update_payload).eq("id", company_id_raw).execute()

        if getattr(update_response, "error", None):
            st.error(f"❌ Update failed: {update_response.data}")
        else:
            st.success("✅ Company info updated.")



# --- Contacts ---
st.subheader("📇 Contacts Overview")

company_id = company_id_raw

# Fetch reps (users) for assignment/updated_by
users_response = supabase.table("users").select("id, name").execute()
reps_list = users_response.data or []
rep_name_to_id = {u["name"]: u["id"] for u in reps_list}

# Fetch contacts for this company
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
                col1, col2 = st.columns(2)

                with col1:
                    full_name = st.text_input("Full Name", value=contact.get("full_name", ""))
                    email = st.text_input("Email", value=contact.get("email", ""))
                    email_quality = st.selectbox(
                        "Email Quality",
                        quality_options,
                        index=quality_options.index(contact.get("email_quality", "")) if contact.get("email_quality") in quality_options else 0
                    )
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
                    first_contacted_date = st.date_input(
                        "First Contacted Date",
                        value=contact.get("first_contacted_date") if contact.get("first_contacted_date") else None
                    )
                    notes = st.text_area("Notes", value=contact.get("notes", ""))

                with col2:
                    phone = st.text_input("Phone", value=contact.get("phone", ""))
                    phone_quality = st.selectbox(
                        "Phone Quality",
                        quality_options,
                        index=quality_options.index(contact.get("phone_quality", "")) if contact.get("phone_quality") in quality_options else 0
                    )
                    linkedin = st.text_input("LinkedIn", value=contact.get("linkedin", ""))
                    last_call_outcome = st.selectbox(
                        "Last Call Outcome",
                        call_outcomes,
                        index=call_outcomes.index(contact.get("last_call_outcome", "")) if contact.get("last_call_outcome") in call_outcomes else 0
                    )
                    outreach_channels = st.multiselect(
                        "Outreach Channels",
                        outreach_options,
                        default=contact.get("outreach_channels") or []
                    )

                updated_by_name = st.selectbox(
                    "Updated By",
                    [""] + [u["name"] for u in reps_list],
                    index=([""] + [u["name"] for u in reps_list]).index(
                        next((u["name"] for u in reps_list if u["id"] == contact.get("updated_by")), "")
                    )
                )

                submitted = st.form_submit_button("💾 Save Contact")
                if submitted:
                    update_payload = {
                        "full_name": full_name,
                        "email": email,
                        "phone": phone,
                        "linkedin": linkedin,
                        "first_contacted_date": first_contacted_date.isoformat() if first_contacted_date else None,
                        "contact_status": contact_status,
                        "email_quality": email_quality,
                        "phone_quality": phone_quality,
                        "last_call_outcome": last_call_outcome,
                        "outreach_channels": outreach_channels,
                        "notes": notes,
                        "updated_by": rep_name_to_id.get(updated_by_name) if updated_by_name else None
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

with st.form("add_contact_form"):
    new_full_name = st.text_input("Full Name")
    new_email = st.text_input("Email")
    new_phone = st.text_input("Phone")
    new_linkedin = st.text_input("LinkedIn")
    new_contact_status = st.selectbox(
        "Contact Status",
        ["", "bounced", "replied", "interested", "not interested", "needs follow-up", "no response"],
        index=0
    )
    new_email_quality = st.selectbox("Email Quality", quality_options, index=0)
    new_phone_quality = st.selectbox("Phone Quality", quality_options, index=0)
    new_last_call_outcome = st.selectbox("Last Call Outcome", call_outcomes, index=0)
    new_outreach_channels = st.multiselect("Outreach Channels (Mark all platforms contacted)", outreach_options)
    new_notes = st.text_area("Notes")

    new_updated_by = st.selectbox(
        "Updated By",
        [""] + [u["name"] for u in reps_list],
        index=0
    )
    submitted_new = st.form_submit_button("➕ Add Contact")
    if submitted_new:
        insert_payload = {
            "full_name": new_full_name,
            "email": new_email,
            "phone": new_phone,
            "linkedin": new_linkedin,
            "contact_status": new_contact_status,
            "email_quality": new_email_quality,
            "phone_quality": new_phone_quality,
            "last_call_outcome": new_last_call_outcome,
            "outreach_channels": new_outreach_channels,
            "notes": new_notes,
            "updated_by": rep_name_to_id.get(new_updated_by) if new_updated_by else None,
            "company_id": company_id
        }
        insert_response = supabase.table("contacts").insert(insert_payload).execute()
        if hasattr(insert_response, "error") and insert_response.error:
            st.error(f"❌ Add failed: {insert_response.error.message}")
        else:
            st.success("✅ Contact added.")
            st.rerun()
