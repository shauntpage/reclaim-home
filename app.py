import streamlit as st
import pandas as pd
import base64
import json
from openai import OpenAI

# --- 1. SETTINGS & INITIALIZATION ---
st.set_page_config(page_title="Reclaim | FIGJAM", page_icon="🏠", layout="centered")

# Ensure all session state keys exist
for key in ['assets', 'current_asset', 'show_diagnostics']:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'assets' else (None if key == 'current_asset' else False)

# --- 2. THE BRAIN (AI ANALYZER) ---
def analyze_image(img_file):
    client = OpenAI(api_key=st.secrets["MY_NEW_KEY"]) 
    base64_image = base64.b64encode(img_file.getvalue()).decode('utf-8')

    prompt = """
    Identify the home asset or consumable in this image. 
    Return a JSON object with these EXACT keys:
    {
      "manufacturer": "Brand",
      "model_number": "Model String",
      "is_consumable": true/false,
      "health_score": 1-10, 
      "birth_year": 2020,
      "avg_lifespan": 15,
      "estimated_value": "$500",
      "estimated_replacement_cost": "$1200",
      "replace_vs_repair": "Strategic advice",
      "modern_alternative": "Name of replacement",
      "reorder_link": "https://www.google.com/search?q=replacement+part",
      "diagnostics": {
          "primary_fault_prediction": "Likely failure",
          "diy_fix_steps": "1. Step one... 2. Step two..."
      }
    }
    Note: For consumables (filters, etc), health_score is % remaining (7=70%). 
    Avg_lifespan for consumables is in MONTHS. Baseline year is 2026.
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
    return json.loads(response.choices[0].message.content)

# --- 3. THE SIDEBAR (COMMAND CENTER) ---
with st.sidebar:
    st.title("🏠 FIGJAM")
    st.subheader("Mischka Scan")
    
    input_method = st.radio("Input Source:", ["Camera", "Upload"], horizontal=True)
    img_file = st.camera_input("Scan Label") if input_method == "Camera" else st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

    if img_file:
        with st.spinner("Analyzing Asset..."):
            st.session_state.current_asset = analyze_image(img_file)
            st.toast("Scan Success!", icon="🚀")

    st.divider()
    if st.button("🗑️ Reset Ledger", use_container_width=True):
        st.session_state.assets = []
        st.session_state.current_asset = None
        st.rerun()

# --- 4. MAIN UI: NEW SCAN REVIEW ---
if st.session_state.current_asset:
    asset = st.session_state.current_asset
    with st.container(border=True):
        st.subheader(f"Found: {asset.get('manufacturer')} {asset.get('model_number')}")
        
        c1, c2 = st.columns(2)
        if c1.button("📥 Add to Ledger", use_container_width=True, type="primary"):
            st.session_state.assets.append(asset)
            st.session_state.current_asset = None
            st.rerun()
        
        if c2.button("🔧 Diagnose", use_container_width=True):
            st.session_state.show_diagnostics = not st.session_state.get('show_diagnostics', False)

        if st.session_state.get('show_diagnostics', False):
            diag = asset.get('diagnostics', {})
            st.error(f"**Predicted Failure:** {diag.get('primary_fault_prediction')}")
            st.info(f"**DIY Repair Path:** {diag.get('diy_fix_steps')}")

# --- 5. MAIN UI: HOME HEALTH LEDGER ---
st.header("📋 Home Health Ledger")

if not st.session_state.assets:
    st.info("No assets tracked. Scan a manufacturer label to begin your home audit.")
else:
    # Portfolio Financials
    total_val = sum([int(a.get('estimated_value', '$0').replace('$','').replace(',','')) for a in st.session_state.assets])
    st.metric("Total Portfolio Value", f"${total_val:,}")

    # Triage Sorting
    sorted_assets = sorted(st.session_state.assets, key=lambda x: int(x.get('health_score', 5)))

    for item in sorted_assets:
        score = int(item.get('health_score', 5))
        is_cons = item.get('is_consumable', False)
        
        if score <= 4: status, icon = "CRITICAL", "🔴"
        elif score <= 7: status, icon = "WATCH", "🟡"
        else: status, icon = "STABLE", "🟢"
        
        with st.expander(f"{icon} {status} | {item.get('manufacturer')} {item.get('model_number')}"):
            m1, m2 = st.columns(2)
            m1.metric("Current Value", item.get('estimated_value', '$--'))
            m2.metric("Repl. Cost", item.get('estimated_replacement_cost', '$--'))
            
            if is_cons:
                st.write(f"**Supply Level:** {score*10}%")
                st.progress(score/10.0)
            else:
                age = 2026 - int(item.get('birth_year', 2020))
                life = int(item.get('avg_lifespan', 15))
                rem = max(0, life - age)
                st.write(f"**Service Life:** {rem} years left")
                st.progress(max(0.0, min(1.0, rem/life)))
            
            st.link_button(f"🛒 Order Replacement", item.get('reorder_link', '#'), use_container_width=True)
            st.caption(f"Strategy: {item.get('replace_vs_repair')}")

# --- 6. FOOTER ---
st.sidebar.divider()
st.sidebar.caption("FIGJAM v2.5 | 'Mischka' AI Engine")
st.sidebar.caption("San Leandro, CA Demo")
