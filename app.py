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
    # Your OpenAI setup should already be here, just update the prompt and return
    client = OpenAI(api_key=st.secrets["MY_NEW_KEY"]) 
    
    prompt = """
    Identify the appliance in this image. You MUST return a JSON object with these keys:
    {
      "manufacturer": "Brand",
      "model_number": "Model String",
      "birth_year": 2018, 
      "avg_lifespan": 15,
      "health_score": 7,
      "replace_vs_repair": "Detailed recommendation based on age vs typical life",
      "modern_alternative": "A current efficient model name",
      "maintenance_alert": "One pro-tip for this specific unit"
    }
    Note: If the exact birth year isn't visible, estimate it based on the design era.
    """

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

with tab1:
    st.subheader("Mischka Protocol: Active Scan")
    
    # User selects how to provide the image
    input_method = st.radio("Select Input:", ["Camera", "Upload File"], horizontal=True)
    
    if input_method == "Camera":
        img_file = st.camera_input("Scan Appliance Label")
    else:
        img_file = st.file_uploader("Upload Label Photo", type=['jpg', 'png', 'jpeg'])

    # Logic to process the image
    if img_file:
        with st.spinner("Mischka is identifying lifecycle data..."):
            # This calls the upgraded function we built
            asset_data = analyze_image(img_file)
            st.session_state.current_asset = asset_data
            
            # Save to temporary session inventory
            if asset_data not in st.session_state.assets:
                st.session_state.assets.append(asset_data)

    # --- DISPLAY RESULTS (Aligned inside Tab 1) ---
    if st.session_state.current_asset:
        asset = st.session_state.current_asset
        st.divider()
        
        # Identity Row
        c1, c2 = st.columns(2)
        c1.metric("Make", asset.get('manufacturer'))
        c2.metric("Model", asset.get('model_number'))

        # Lifecycle Health Section
        st.write("### 🩺 Home Asset Health")
        
        current_year = 2026
        birth = int(asset.get('birth_year', 2020))
        lifespan = int(asset.get('avg_lifespan', 15))
        age = current_year - birth
        remaining = max(0, lifespan - age)
        health_score = int(asset.get('health_score', 5))
        
        # Visual Progress
        st.progress(health_score / 10, text=f"Health Status: {health_score}/10")
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Age", f"{age} yrs")
        col_b.metric("Avg. Life", f"{lifespan} yrs")
        col_c.metric("Life Left", f"~{remaining} yrs")

        with st.container(border=True):
            st.write("#### 💡 Economic Advice")
            st.warning(f"**Decision:** {asset.get('replace_vs_repair')}")
            st.info(f"**Upgrade:** {asset.get('modern_alternative')}")

with tab2:
    st.subheader("📋 Home Health Ledger")
    
    if st.session_state.assets:
        # 1. Sort the assets so Red (Critical) always floats to the top
        # This forces the user to confront the most 'at-risk' items first
        sorted_assets = sorted(st.session_state.assets, key=lambda x: x.get('health_score', 5))
        
        st.write("Review your asset health below. Items are ranked by urgency.")
        st.divider()

       for item in sorted_assets:
            score = item.get('health_score', 5)
            
            # 1. Determine Status Branding
            if score <= 4:
                status, label_color = "🔴 CRITICAL", "red"
            elif score <= 7:
                status, label_color = "🟡 WATCH", "orange"
            else:
                status, label_color = "🟢 STABLE", "green"
            
            # 2. The Interactive Card (Expander)
            with st.expander(f"{status} | {item.get('manufacturer')} {item.get('model_number')}"):
                
                # Top Row: The Financial Reality
                c1, c2 = st.columns(2)
                c1.metric("Est. Value", item.get('estimated_value', '$--'))
                c2.metric("Replacement", item.get('estimated_replacement_cost', '$--'))
                
                st.divider()

                # Middle Row: The Life Clock
                st.write("#### ⏳ Lifecycle Analysis")
                age = 2026 - int(item.get('birth_year', 2020))
                life = int(item.get('avg_lifespan', 15))
                remaining = max(0, life - age)
                
                st.progress(max(0.0, min(1.0, remaining / life)), text=f"{remaining} years of service left")
                
                col_a, col_b = st.columns(2)
                col_a.write(f"**Age:** {age} years")
                col_b.write(f"**Avg. Lifespan:** {life} years")

                # Bottom Row: The "Mischka" Insight
                with st.container(border=True):
                    st.write("#### 💡 Strategic Advice")
                    st.info(f"**Action:** {item.get('replace_vs_repair')}")
                    st.warning(f"**Likely Fault:** {item.get('diagnostics', {}).get('primary_fault_prediction')}")
                    st.success(f"**Modern Upgrade:** {item.get('modern_alternative')}")
            
            # 3. Draw the Status Card
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                c1.write(f"### {item.get('manufacturer')} {item.get('model_number')}")
                c2.write(f"**{status}**")
                
                # Useful Life Progress Bar
                age = 2026 - int(item.get('birth_year', 2020))
                life = int(item.get('avg_lifespan', 15))
                remaining = max(0, life - age)
                
                # Calculate the percentage of life remaining for the bar
                life_pct = max(0.0, min(1.0, remaining / life))
                
                st.progress(life_pct, text=f"{remaining} years of estimated service remaining")
                
                # Mini-metrics for the card
                m1, m2, m3 = st.columns(3)
                m1.caption(f"Age: {age} yrs")
                m2.caption(f"Total Life: {life} yrs")
                m3.caption(f"Score: {score}/10")

        if st.button("Clear Session Ledger", use_container_width=True):
            st.session_state.assets = []
            st.session_state.current_asset = None
            st.rerun()
    else:
        st.info("Your ledger is currently empty. Head over to the 'Scan' tab to audit your first appliance.")
