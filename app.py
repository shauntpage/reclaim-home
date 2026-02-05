import streamlit as st
import base64
import json
from openai import OpenAI

# --- 1. APP CONFIG & "THUMB-FRIENDLY" CSS ---
st.set_page_config(page_title="FIGJAM", page_icon="🏠", layout="centered")

st.markdown("""
    <style>
    /* Make buttons massive and tap-friendly */
    div.stButton > button { 
        width: 100%; 
        height: 80px; 
        font-size: 24px !important; 
        font-weight: 600;
        border-radius: 20px; 
        margin-bottom: 16px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    /* Clean up the metrics to look like dashboard tiles */
    .stMetric { 
        background-color: #f7f9fc; 
        border: 1px solid #e1e4e8; 
        padding: 20px; 
        border-radius: 15px; 
        text-align: center;
    }
    /* Hide the default hamburger menu for a cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# State Management
for key in ['assets', 'page', 'chat_history', 'current_asset']:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ['assets', 'chat_history'] else ("home" if key == 'page' else None)

client = OpenAI(api_key=st.secrets["MY_NEW_KEY"])

# --- 2. THE BRAIN ---
def analyze_universal(img_file):
    base64_image = base64.b64encode(img_file.getvalue()).decode('utf-8')
    prompt = """
    Analyze image (Appliance, Vehicle, or Consumable). Return JSON:
    {
      "manufacturer": "Brand", "model_number": "Model", 
      "is_consumable": bool, "health_score": 1-10, 
      "birth_year": 2020, "avg_lifespan": 15,
      "estimated_value": "$500",
      "replace_vs_repair": "Strategy", "reorder_link": "URL",
      "diagnostics": {"primary_fault_prediction": "Fault", "diy_fix_steps": "Steps"}
    }
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- 3. PAGE: HOME (THE MENU) ---
if st.session_state.page == "home":
    st.title("🏠 FIGJAM")
    
    # BIG BUTTON 1: The "Audit" (Home Buying / Inventory)
    if st.button("📸 SCAN ASSET"):
        st.session_state.page = "scan"; st.rerun()
        
    # BIG BUTTON 2: The "Emergency" (Ad Hoc Fix)
    if st.button("🆘 AD HOC FIX"):
        st.session_state.current_asset = {"manufacturer": "Quick", "model_number": "Fix"}
        st.session_state.chat_history = [{"role": "assistant", "content": "Mischka here. I'm listening. What's broken?"}]
        st.session_state.page = "diagnose"; st.rerun()

    # BIG BUTTON 3: The "Equity" (View Ledger)
    if st.button("📋 MY LEDGER"):
        st.session_state.page = "ledger"; st.rerun()

    # The "Scoreboard"
    if st.session_state.assets:
        val = sum([int(str(a.get('estimated_value', '0')).replace('$','').replace(',','')) for a in st.session_state.assets])
        st.metric("Total Asset Value", f"${val:,}")

# --- 4. PAGE: SCAN (AUTO-SAVE) ---
elif st.session_state.page == "scan":
    if st.button("❌ CANCEL"): st.session_state.page = "home"; st.rerun()
    
    img = st.camera_input("Point at Label")
    if img:
        with st.spinner("Identifying..."):
            asset = analyze_universal(img)
            st.session_state.assets.append(asset) # Auto-save
            st.toast("Saved to Ledger!", icon="✅")
            st.session_state.page = "ledger"; st.rerun()

# --- 5. PAGE: LEDGER (THE DASHBOARD) ---
elif st.session_state.page == "ledger":
    if st.button("🏠 HOME"): st.session_state.page = "home"; st.rerun()
    st.subheader("Your Assets")
    
    if not st.session_state.assets:
        st.info("Ledger empty.")
    else:
        # Sort by urgency
        sorted_assets = sorted(st.session_state.assets, key=lambda x: int(x.get('health_score', 5)))
        
        for i, item in enumerate(sorted_assets):
            score = int(item.get('health_score', 5))
            icon = "🔴" if score <= 4 else ("🟡" if score <= 7 else "🟢")
            
            with st.expander(f"{icon} {item.get('manufacturer')} {item.get('model_number')}"):
                # The "Gauge" Logic
                if item.get('is_consumable'):
                    st.progress(score/10.0, text=f"Supply: {score*10}%")
                else:
                    age = 2026 - int(item.get('birth_year', 2020))
                    rem = max(0, int
