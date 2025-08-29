import streamlit as st
from supabase import create_client, Client
import uuid
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from st_aggrid.shared import GridUpdateMode

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
        "id, name, industry, city, source, state, sf_occupied, lease_expiration, future_move, created_at, contact_status"
    ).execute()
    df = pd.DataFrame(response.data)

    # Clean string columns
    for col in ["state", "name", "industry", "city", "source"]:
        df[col] = df[col].astype(str).str.strip().replace("nan", "")

    # Clean sf_occupied safely
    def safe_parse_sf(value):
        try:
            return float(str(value).replace(",", "").strip())
        except:
            return None

    df["sf_occupied"] = df["sf_occupied"].apply(safe_parse_sf)

    # Ensure contact_status exists
    if "contact_status" not in df.columns:
        df["contact_status"] = "Not contacted"

    return df


def company_list_view():
    st.set_page_config(page_title="Company List", layout="wide")
    st.title("Company List")

    # --- Load companies into session_state for persistence ---
    if "companies_df" not in st.session_state:
        st.session_state["companies_df"] = load_companies()

    df = st.session_state["companies_df"].copy()

    # --- Filters ---
    search_term = st.text_input("Search by company name")
    if search_term:
        df = df[df['name'].str.contains(search_term, case=False, na=False)]

    df['industry'] = df['industry'].fillna("Unknown")
    industries = sorted(df['industry'].unique().tolist())
    selected_industry = st.selectbox("Filter by Industry", ["All"] + industries)
    if selected_industry != "All":
        df = df[df['industry'] == selected_industry]

    df['source'] = df['source'].fillna("Unknown")
    sources = sorted(df['source'].unique().tolist())
    selected_source = st.selectbox("Filter by Source", ["All"] + sources)
    if selected_source != "All":
        df = df[df['source'] == selected_source]

    df["state"] = df["state"].fillna("Unknown").astype(str).str.strip()
    states = sorted([s for s in df["state"].unique().tolist() if s])
    selected_state = st.selectbox("Filter by State", ["All"] + states)
    if selected_state != "All":
        df = df[df["state"] == selected_state]

    # --- SF Occupied numeric filter ---
    df["sf_occupied_num"] = pd.to_numeric(
        df["sf_occupied"].astype(str).str.replace(",", "").str.strip(),
        errors="coerce"
    )
    if df["sf_occupied_num"].notna().any():
        sf_min_value = int(df["sf_occupied_num"].min() // 1000 * 1000)
        sf_max_value = int(df["sf_occupied_num"].max() // 1000 * 1000 + 1000)
        sf_min, sf_max = st.slider(
            "Select SF Occupied range:",
            min_value=sf_min_value,
            max_value=sf_max_value,
            value=(sf_min_value, sf_max_value),
            step=1000,
        )
        df = df[(df["sf_occupied_num"] >= sf_min) & (df["sf_occupied_num"] <= sf_max)]
    df = df.drop(columns=["sf_occupied_num"])

    # --- Lease expiration filter ---
    df["lease_expiration"] = pd.to_datetime(df["lease_expiration"], errors="coerce")
    lease_min = df["lease_expiration"].min() if df["lease_expiration"].notna().any() else pd.Timestamp("2000-01-01")
    lease_max = df["lease_expiration"].max() if df["lease_expiration"].notna().any() else pd.Timestamp.today()
    lease_date_range = st.date_input("Lease Expiration between", [lease_min, lease_max])
    start_dt = pd.to_datetime(lease_date_range[0])
    end_dt = pd.to_datetime(lease_date_range[1])
    df = df[df["lease_expiration"].isna() | ((df["lease_expiration"] >= start_dt) & (df["lease_expiration"] <= end_dt))]

    # --- Future move date filter ---
    df["future_move"] = pd.to_datetime(df["future_move"], errors="coerce")
    if df["future_move"].notna().any():
        move_min = df["future_move"].min()
        move_max = df["future_move"].max()
        move_date_range = st.date_input("Future Move between", [move_min, move_max])
        move_start = pd.to_datetime(move_date_range[0])
        move_end = pd.to_datetime(move_date_range[1])
        df = df[df["future_move"].isna() | ((df["future_move"] >= move_start) & (df["future_move"] <= move_end))]

    # --- Date Uploaded (Created_at) filter ---
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")

    # Normalize timezone differences: strip timezone if present
    if pd.api.types.is_datetime64tz_dtype(df["created_at"]):
        df["created_at"] = df["created_at"].dt.tz_convert(None)

    if df["created_at"].notna().any():
        # Work with just the date part
        df["created_date"] = df["created_at"].dt.date  

        upload_min = df["created_date"].min()
        upload_max = df["created_date"].max()

        upload_date_range = st.date_input("Date Uploaded between", [upload_min, upload_max])

        if len(upload_date_range) == 2:
            upload_start = upload_date_range[0]
            upload_end = upload_date_range[1]
            df = df[df["created_date"].between(upload_start, upload_end)]


    if df.empty:
        st.warning("No companies found with the selected filters.")
        return

    # --- Reset index after filtering ---
    df = df.reset_index(drop=True)

    # --- Add Serial Number (Sl No) ---
    df.insert(0, "Sl No", range(1, len(df) + 1))

    # --- Show total rows dynamically ---
    st.markdown(f"**Total companies: {len(df)}**")

    # --- Updated Dropdown options ---
    status_options = [
        "Not contacted",
        "Missing contact info",
        "No response",
        "Not interested",
        "Interested",
        "Follow-up",
        "Working",
        "Contact Updated"   # NEW option
    ]

    # --- Map statuses to colors ---
    status_colors = {
        "Not contacted": "#d3d3d3",        # light gray
        "Missing contact info": "#ffa500", # orange
        "No response": "#ff6961",          # red
        "Not interested": "#c23b22",       # dark red
        "Interested": "#77dd77",           # green
        "Follow-up": "#ffd700",            # yellow
        "Working": "#87ceeb",              # blue
        "Contact Updated": "#9370DB"       # purple
    }

    # --- JsCode renderer for clickable company name ---
    anchor_renderer = JsCode("""
    class AnchorRenderer {
        init(params) {
            const span = document.createElement('span');
            span.textContent = params.value || params.data.name || '';
            span.style.color = '#1f77b4';
            span.style.textDecoration = 'underline';
            span.style.cursor = 'pointer';
            span.addEventListener('click', function(e) {
                e.stopPropagation();
                window.open('/company_detail?company_id=' + params.data.id, '_blank');
            });
            this.eGui = span;
        }
        getGui() { return this.eGui; }
    }
    """)

    # --- JsCode for coloring Contact Status cells ---
    status_color_renderer = JsCode(f"""
    function(params) {{
        let bg = 'white';
        let text = 'black';
        const colors = {status_colors};
        if(params.value in colors) {{
            bg = colors[params.value];
        }}
        return {{ 'background-color': bg, 'color': text, 'font-weight': 'bold' }};
    }}
    """)

    # --- Build AG Grid ---
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(editable=False)

    gb.configure_column("Sl No", header_name="Sl No", editable=False, width=70)
    gb.configure_column("name", header_name="Company Name", editable=False, cellRenderer=anchor_renderer)
    gb.configure_column(
        "contact_status",
        header_name="Contact Status",
        editable=True,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": status_options},
        cellStyle=status_color_renderer
    )

    grid_options = gb.build()

    # --- Render AG Grid in fully responsive height ---
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        data_return_mode="AS_INPUT",
        fit_columns_on_grid_load=True,
        height=st.session_state.get("window_height", 700),
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True
    )

    # --- Save updated rows automatically ---
    updated_df = pd.DataFrame(grid_response["data"])
    for _, row in updated_df.iterrows():
        idx = st.session_state["companies_df"].index[
            st.session_state["companies_df"]["id"] == row["id"]
        ]
        if not idx.empty:
            i = idx[0]
            old_status = st.session_state["companies_df"].at[i, "contact_status"]
            new_status = row["contact_status"]
            if old_status != new_status:
                supabase.table("companies").update({"contact_status": new_status}).eq("id", row["id"]).execute()
                st.session_state["companies_df"].at[i, "contact_status"] = new_status


def company_detail_view(company_id):
    st.write("Company detail view placeholder (unchanged).")


def main():
    st.set_page_config(page_title="Lead Management System", layout="wide")

    query_params = st.query_params
    company_id_raw = query_params.get("company_id", None)

    if company_id_raw:
        if isinstance(company_id_raw, (list, tuple)):
            company_id_raw = company_id_raw[0]
        company_detail_view(company_id_raw)
    else:
        company_list_view()


if __name__ == "__main__":
    main()
