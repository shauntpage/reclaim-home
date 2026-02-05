import streamlit as st
from openai import OpenAI
import base64
import json
import pandas as pd

# 1. PAGE SETUP
st.set_page_config(page_title="Reclaim Home Prototype", page_icon="🏠")

# 2. THE BOUNCER (PASSWORD CHECK)
def check_password():
    """Returns `True` if the user had the correct password."""
    
    if "APP_PASSWORD" not in st.secrets:
        st.error("Setup Error: Please add APP_PASSWORD to your Streamlit Secrets.")
        return False

    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Clear the box
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Enter Password to Access Reclaim Home:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Enter Password to Access Reclaim Home:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# 3. SECURELY LOAD API KEY
try:
    client = OpenAI(api_key=st.secrets["MY_NEW_KEY"])
except:
    st.error("API Key missing! Add MY_NEW_KEY to Streamlit Secrets.")
    st.stop()

# --- APP LOGIC ---

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def analyze_image(img_file):
    client = OpenAI(api_key=st.secrets["MY_NEW_KEY"]) 
    
    # Convert image to base64 for the model
    base64_image = base64.b64encode(img_file.getvalue()).decode('utf-8')

    prompt = """
    Identify the item in this image. You MUST return a JSON object with these EXACT keys:
    {
      "manufacturer": "Brand",
      "model_number": "Model String",
      "is_consumable": true,
      "health_score": 7, 
      "birth_year": 2020,
      "avg_lifespan": 15,
      "estimated_value": "$500",
      "estimated_replacement_cost": "$1200",
      "replace_vs_repair": "Recommendation based on age and condition",
      "modern_alternative": "Name of replacement or upgrade",
      "reorder_link": "https://www.google.com/search?q=replacement+part+model",
      "diagnostics": {
          "primary_fault_prediction": "Likely mechanical failure or end of life",
          "diy_fix_steps": "Step 1: ... Step 2: ..."
      }
    }
    
    CRITICAL INSTRUCTIONS:
    1. If the item is a filter, battery, or supply, set 'is_consumable' to true.
    2. 'health_score' is 1-10. For consumables, it represents % of life left (e.g., 7 = 70%).
    3. For consumables, 'avg_lifespan' should be in MONTHS, not years.
    4. Provide a direct search link in 'reorder_link' for the specific part.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ],
            }
        ],
        response_format={"type": "json_object"}
    )
    
    # Parse and return the JSON
    return json.loads(response.choices[0].message.content)
    # Assuming you are using the vision model logic:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img_file.read()).decode()}"}}
        ]}],
        response_format={ "type": "json_object" }
    )
    import json
    return json.loads(response.choices[0].message.content)

def get_diy_advice(model_info, symptom):
    prompt = f"""
    The user has a {model_info.get('manufacturer')} {model_info.get('category')} 
    Model: {model_info.get('model_number')}.
    Symptom: "{symptom}".
    
    Return JSON with:
    - likely_cause (string)
    - steps (array of strings)
    - safety_warning (string)
    """
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[{"role": "system", "content": "You are an expert handyman AI."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- UI LAYOUT ---
st.title("Reclaim 🏠")

if 'assets' not in st.session_state: st.session_state.assets = []
if 'current_asset' not in st.session_state: st.session_state.current_asset = None
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

# --- TAB DEFINITIONS ---
tab1, tab2 = st.tabs(["🔍 Scan Asset", "📋 My Inventory"])

# --- INITIALIZATION (Ensure this is near the top of your script) ---
for key in ['assets', 'current_asset', 'show_diagnostics']:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'assets' else (None if key == 'current_asset' else False)

# --- TAB DEFINITIONS ---
tab1, tab2 = st.tabs(["🔍 Scan Asset", "📋 My Ledger"])

with tab1:
    st.subheader("Mischka Protocol: Active Scan")
    
    # 1. THE TOGGLE (Cleaning up the UI)
    input_method = st.radio("Choose Input Method:", ["Camera", "Upload Photo"], horizontal=True)
    
    img_file = None
    if input_method == "Camera":
        # Only shows the camera interface
        img_file = st.camera_input("Point at the manufacturer label")
    else:
        # Only shows the file uploader
        img_file = st.file_uploader("Select a photo from your gallery", type=['jpg', 'png', 'jpeg'])

    # 2. THE SCANNING LOGIC
    if img_file:
        with st.spinner("Mischka is identifying lifecycle and supply data..."):
            asset_data = analyze_image(img_file)
            st.session_state.current_asset = asset_data

    if st.session_state.current_asset:
        asset = st.session_state.current_asset
        st.divider()
        
        # Identity Header
        st.header(f"📦 {asset.get('manufacturer')} {asset.get('model_number')}")
        
        # --- DUAL-MODE DISPLAY (Consumable vs. Appliance) ---
        is_consumable = asset.get('is_consumable', False)
        score = int(asset.get('health_score', 5))
        
        if is_consumable:
            st.subheader("⛽ Supply Level")
            st.progress(score / 10.0, text=f"{score*10}% Remaining")
            st.write(f"**Replacement Cycle:** Every {asset.get('avg_lifespan')} months")
        else:
            st.subheader("🩺 Asset Health")
            # Baseline Year is 2026
            age = 2026 - int(asset.get('birth_year', 2020))
            life = int(asset.get('avg_lifespan', 15))
            remaining = max(0, life - age)
            # Progress bar shows % of life left
            life_pct = max(0.0, min(1.0, remaining / life))
            st.progress(life_pct, text=f"{remaining} years of service left")

        # --- COMMAND CENTER ---
        st.write("### ⚡ Actions")
        c_inv, c_diag = st.columns(2)
        
        if c_inv.button("📥 Add to Ledger", use_container_width=True):
            if asset not in st.session_state.assets:
                st.session_state.assets.append(asset)
                st.toast("Saved to Home Ledger!", icon="✅")
            else:
                st.toast("Already in Ledger", icon="ℹ️")

        if c_diag.button("🔧 Deep Diagnose", use_container_width=True):
            st.session_state.show_diagnostics = True

        if st.session_state.get('show_diagnostics', False):
            with st.container(border=True):
                st.subheader("👨‍🔧 Master Tech Report")
                diag = asset.get('diagnostics', {})
                st.error(f"**Likely Fault:** {diag.get('primary_fault_prediction', 'N/A')}")
                st.info(f"**Mischka's Repair Path:** \n\n {diag.get('diy_fix_steps', 'Model-specific fix not found.')}")
                if st.button("Close Report"):
                    st.session_state.show_diagnostics = False
                    st.rerun()

with tab2:
    st.subheader("📋 Home Health Ledger")
    
    if st.session_state.assets:
        # Sort by urgency (Lowest score = Red = Top of list)
        sorted_assets = sorted(st.session_state.assets, key=lambda x: int(x.get('health_score', 5)))
        
        st.write("Review your home's prioritized risk map below.")
        
        for item in sorted_assets:
            s = int(item.get('health_score', 5))
            is_cons = item.get('is_consumable', False)
            
            # Triage Branding
            if s <= 4: status = "🔴 CRITICAL"
            elif s <= 7: status = "🟡 WATCH"
            else: status = "🟢 STABLE"
            
            # THE DRILL-DOWN CARD
            with st.expander(f"{status} | {item.get('manufacturer')} {item.get('model_number')}"):
                c1, c2 = st.columns(2)
                c1.metric("Current Value", item.get('estimated_value', '$--'))
                c2.metric("Repl. Cost", item.get('estimated_replacement_cost', '$--'))
                
                st.divider()
                
                # Dynamic Logic for Ledger Details
                if is_cons:
                    st.write(f"**Supply:** {s*10}% Remaining")
                    st.progress(s/10.0)
                else:
                    age = 2026 - int(item.get('birth_year', 2020))
                    life = int(item.get('avg_lifespan', 15))
                    rem = max(0, life - age)
                    st.write(f"**Service Life:** {rem} years left (Age: {age} yrs)")
                    st.progress(max(0.0, min(1.0, rem / life)))
                
                # THE MONETIZATION ENGINE (Reorder Button)
                reorder_url = item.get('reorder_link', 'https://www.google.com/search?q=' + item.get('model_number'))
                st.link_button(f"🛒 Quick Reorder Replacement", reorder_url, use_container_width=True, type="primary")
                
                st.info(f"**Mischka's Take:** {item.get('replace_vs_repair', 'N/A')}")

        if st.button("Purge Session Data", use_container_width=True):
            st.session_state.assets = []
            st.rerun()
    else:
        st.info("Your ledger is empty. Head to 'Scan Asset' to begin your home audit.")

# --- SIDEBAR / FOOTER ---
st.sidebar.divider()
st.sidebar.caption("FIGJAM Alpha | Mischka Protocol v2.5")
st.sidebar.caption("Prioritizing Home Equity through Data.")


