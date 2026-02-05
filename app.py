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
        # Helper function to prevent sorting syntax errors
        def get_score(a):
            return int(a.get('health_score', 5))
            
        # Clean sort
        sorted_assets = sorted(st.session_state.assets, key=get_score)
        
        for i, item in enumerate(sorted_assets):
            score = int(item.get('health_score', 5))
            icon = "🔴" if score <= 4 else ("🟡" if score <= 7 else "🟢")
            
            with st.expander(f"{icon} {item.get('manufacturer')} {item.get('model_number')}"):
                
                # The "Gauge" Logic
                if item.get('is_consumable'):
                    st.progress(score/10.0, text=f"Supply: {score*10}%")
                else:
                    # Broken down math to prevent bracket errors
                    birth_year = int(item.get('birth_year', 2020))
                    lifespan = int(item.get('avg_lifespan', 15))
                    age = 2026 - birth_year
                    rem = max(0, lifespan - age)
                    
                    fraction = 0.0
                    if lifespan > 0:
                        fraction = max(0.0, min(1.0, rem / lifespan))
                        
                    st.progress(fraction, text=f"{rem} Years Left")

                c1, c2 = st.columns(2)
                if c1.button("🔧 FIX", key=f"f{i}"):
                    st.session_state.current_asset = item
                    st.session_state.chat_history = [{"role": "assistant", "content": f"Troubleshooting {item.get('manufacturer')}. What's wrong?"}]
                    st.session_state.page = "diagnose"; st.rerun()
                c2.link_button("🛒 BUY", item.get('reorder_link', '#'))

    if st.button("🗑️ RESET APP", type="secondary"):
        st.session_state.assets = []; st.rerun()

# --- 6. PAGE: DIAGNOSE (CHAT) ---
elif st.session_state.page == "diagnose":
    if st.button("⬅️ DONE"): st.session_state.chat_history = []; st.session_state.page = "home"; st.rerun()
    
    # Chat Interface
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if prompt := st.chat_input("Type symptoms..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        with st.chat_message("assistant"):
            # Context injection
            asset = st.session_state.current_asset
            ctx = f"You are Mischka. Asset: {asset.get('manufacturer')} {asset.get('model_number')}. Fault: {asset.get('diagnostics', {}).get('primary_fault_prediction')}."
            res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": ctx}] + st.session_state.chat_history)
            ans = res.choices[0].message.content
            st.write(ans)
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
