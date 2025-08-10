import pandas as pd
from supabase import create_client, Client

# Supabase credentials
SUPABASE_URL = "https://qrvdfqzmaupqqjxsqezu.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFydmRmcXptYXVwcXFqeHNxZXp1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ1ODE5MTgsImV4cCI6MjA3MDE1NzkxOH0.c93JH5Kf3CV8uamfV3-nwbzjn5HnBEwmU7KApNcwZIU"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def format_date(d):
    if d is None or pd.isna(d) or d == "":
        return None
    if isinstance(d, str):
        return d  # assume already a valid date string
    return pd.to_datetime(d).strftime("%Y-%m-%d")

def get_or_create_company(company_name, company_data):
    if not company_name or company_name.strip() == "":
        print("⚠️ Skipping company with empty name")
        return None

    company_name_clean = company_name.strip().lower()
    response = supabase.table("companies").select("*").execute()

    if response.data is None:
        print("Error fetching companies:", response)
        return None

    existing = [c for c in response.data if c['name'].strip().lower() == company_name_clean]
    if existing:
        return existing[0]['id']

    insert_data = {
        "name": company_name.strip(),
        "industry": company_data.get("industry"),
        "size": company_data.get("size"),
        "website": company_data.get("website"),
        "source": company_data.get("source"),
        "location": company_data.get("location"),
        "city": company_data.get("city"),
        "state": company_data.get("state"),
        "zip": company_data.get("zip"),
        "imported_at": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "lease_expiration": format_date(company_data.get("lease_expiration")),
        "future_move": format_date(company_data.get("future_move")),
        "landlord": company_data.get("landlord"),
        "landlord_rep": company_data.get("landlord_rep"),
        "tenant_rep": company_data.get("tenant_rep"),
        "floor": company_data.get("floor"),
        "space_use": company_data.get("space_use"),
        "sf_occupied": company_data.get("sf_occupied"),
    }
    insert_resp = supabase.table("companies").insert(insert_data).execute()
    if not insert_resp.data:
        print(f"❌ Error inserting company '{company_name}'")
        return None
    return insert_resp.data[0]['id']


def insert_contact(company_id, contact_data):
    if not contact_data.get("full_name") or contact_data.get("full_name").strip() == "":
        print("⚠️ Skipping contact with empty full_name")
        return None

    insert_data = {
        "full_name": contact_data.get("full_name").strip(),
        "title": contact_data.get("title"),
        "email": contact_data.get("email"),
        "phone": contact_data.get("phone"),
        "company_id": company_id,
        "linkedin": contact_data.get("linkedin"),
    }
    response = supabase.table("contacts").insert(insert_data).execute()
    if not response.data:
        print(f"❌ Error inserting contact '{contact_data.get('full_name')}'")
        return None
    return response.data[0]['id']

def insert_lead(company_id, contact_id, lead_data):
    insert_data = {
        "company_id": company_id,
        "contact_id": contact_id,
        "status": lead_data.get("status", "new"),
        "stage": lead_data.get("stage"),
        "assigned_to": lead_data.get("assigned_to"),
        "priority": lead_data.get("priority"),
        "source": lead_data.get("source"),
        "lost_reason": lead_data.get("lost_reason"),
        "region": lead_data.get("region"),
        "campaign_name": lead_data.get("campaign_name"),
        "notes": lead_data.get("notes"),
        "next_followup_date": format_date(lead_data.get("next_followup_date")),
        "last_contacted": format_date(lead_data.get("last_contacted")),
    }
    response = supabase.table("leads").insert(insert_data).execute()
    if not response.data:
        print(f"❌ Error inserting lead for contact_id '{contact_id}'")
        return None
    return response.data[0]['id']

def process_apollo_row(row):
    company_data = {
        "industry": None,
        "size": None,
        "website": row.get("website"),
        "source": "apollo",
        "location": None,
        "city": None,
        "state": None,
        "zip": None,
    }
    company_name = row.get("company_name")

    contact_data = {
        "full_name": f"{row.get('first_name', '')} {row.get('last_name', '')}".strip(),
        "title": row.get("job_title"),
        "email": row.get("email"),
        "phone": None,
        "linkedin": None,
    }

    lead_data = {
        "source": "apollo",
        "status": "new"
    }

    return company_name, company_data, contact_data, lead_data

def process_costar_row(row):
    company_data = {
        "industry": None,
        "size": None,
        "website": None,
        "source": "costar",
        "location": row.get("Address"),
        "city": row.get("City"),
        "state": None,
        "zip": None,
        "lease_expiration": row.get("Lease Expiration"),
        "future_move": row.get("Future Move"),
        "landlord": row.get("Landlord"),
        "landlord_rep": row.get("Landlord Representative"),
        "tenant_rep": row.get("Tenant Representative"),
        "floor": row.get("Floor"),
        "space_use": row.get("Space Use"),
        "sf_occupied": row.get("SF Occupied"),
    }
    company_name = row.get("Tenant Name")

    contact_data = {
        "full_name": row.get("Best Tenant Contact"),
        "title": None,
        "email": row.get("Tenant Email Id"),
        "phone": row.get("Best Tenant Phone"),
        "linkedin": None,
    }

    lead_data = {
        "source": "costar",
        "status": "new"
    }

    return company_name, company_data, contact_data, lead_data

def main():
    apollo_df = pd.read_csv("/Users/kishorekanchan/Downloads/apollo.csv").fillna("")
    costar_df = pd.read_csv("/Users/kishorekanchan/Downloads/costar.csv").fillna("")

    print(f"Processing Apollo rows: {len(apollo_df)}")
    for _, row in apollo_df.iterrows():
        company_name, company_data, contact_data, lead_data = process_apollo_row(row)
        if not company_name or not contact_data["full_name"]:
            print("⚠️ Skipping row due to missing company or contact name")
            continue
        company_id = get_or_create_company(company_name, company_data)
        if company_id is None:
            continue
        contact_id = insert_contact(company_id, contact_data)
        if contact_id is None:
            continue
        insert_lead(company_id, contact_id, lead_data)

    print(f"Processing CoStar rows: {len(costar_df)}")
    for _, row in costar_df.iterrows():
        company_name, company_data, contact_data, lead_data = process_costar_row(row)
        if not company_name or company_name.strip() == "":
            print(f"⚠️ Skipping Costar row due to missing company name")
            continue
        company_id = get_or_create_company(company_name, company_data)
        if company_id is None:
            continue
        if not contact_data["full_name"] or contact_data["full_name"].strip() == "":
            print(f"⚠️ No contact name for company '{company_name}', skipping contact and lead insertion but company is saved")
            continue
        contact_id = insert_contact(company_id, contact_data)
        if contact_id is None:
            continue
        insert_lead(company_id, contact_id, lead_data)

    print("✅ Data upload complete!")

if __name__ == "__main__":
    main()
