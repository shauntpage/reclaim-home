import streamlit as st
import pandas as pd
import base64
import json
from openai import OpenAI

# --- 1. SETTINGS & INITIALIZATION ---
st.set_page_config(page_title="Reclaim | FIGJAM", page_icon="🏠", layout="centered")

# Ensure all session state keys exist
if 'assets' not in st.session_state: st.session_state.assets = []
if 'current_asset' not in st.session_state: st.session_state.current_asset = None
if 'chat_mode' not in st.session_state: st.session_state.chat_mode = False
if 'messages' not in st.session_state: st.session_state.messages = []

# --- 2. THE BRAIN (AI ANALYZER & CHAT) ---
client = OpenAI(api_key=st.secrets["MY_NEW_KEY"])

def analyze_image(img_file):
    base64_image = base64.b64encode(img_file.getvalue()).decode('utf-8')
    prompt = """
    Identify the home asset. Return JSON with:
    {
      "manufacturer": "Brand", "model_number": "Model", "is_consumable": bool,
      "health_score": 1-10, "birth_year": 2020, "avg_lifespan": 15,
      "estimated_value": "$500", "estimated_replacement_cost": "$1200",
      "replace_vs_repair": "Advice", "modern_alternative": "Model",
      "reorder_link": "URL",
      "diagnostics": {"primary_fault_prediction": "Fault", "diy_fix_steps": "Steps"}
    }
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- 3. THE SIDEBAR ---
with st.sidebar:
    st.title("🏠 FIGJAM")
    input_method = st.radio("Input Source:", ["Camera", "Upload"], horizontal=True)
    img_file = st.camera_input("Scan Label") if input_method == "Camera" else st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

    if img_file:
        with st.spinner("Analyzing..."):
            st.session_state.current_asset = analyze_image(img_file)
            st.session_state.chat_mode = False # Reset chat for new scan

    st.divider()
    if st.button("🗑️ Reset Ledger", use_container_width=True):
        st.session_state.assets = []
        st.session_state.current_asset = None
        st.session_state.messages = []
        st.rerun()

# --- 4. MAIN UI: DIAGNOSTIC CHAT MODE ---
if st.session_state.chat_mode and st.session_state.current_asset:
    asset = st.session_state.current_asset
    st.header(f"🔧 Troubleshooting: {asset.get('manufacturer')}")
    
    if st.button("⬅️ Back to Ledger"):
        st.session_state.chat_mode = False
        st.rerun()

    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat Input
    if prompt := st.chat_input(f"Ask Mischka about your {asset.get('model_number')}..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Inject context so the AI knows exactly what we are looking at
            context = f"You are Mischka, a master mechanic. We are looking at a {asset.get('manufacturer')} {asset.get('model_number')}. The predicted fault is {asset.get('diagnostics', {}).get('primary_fault_prediction')}."
            full_history = [{"role": "system", "content": context}] + st.session_state.messages
            
            response = client.chat.completions.create(model="gpt-4o", messages=full_history)
            answer = response.choices[0].message.content
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

# --- 5. MAIN UI: SCAN REVIEW & LEDGER ---
else:
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
                # Initialize chat with the AI's first thought
                st.session_state.messages = [{"role": "assistant", "content": f"I've analyzed your {asset.get('manufacturer')}. It looks like a potential {asset.get('diagnostics', {}).get('primary_fault_prediction')}. How can I help you fix it?"}]
                st.session_state.chat_mode = True
                st.rerun()

    st.header("📋 Home Health Ledger")
    if not st.session_state.assets:
        st.info("No assets tracked. Scan a label to begin.")
    else:
        # Triage Display
        sorted_assets = sorted(st.session_state.assets, key=lambda x: int(x.get('health_score', 5)))
        for item in sorted_assets:
            score = int(item.get('health_score', 5))
            icon = "🔴" if score <= 4 else ("🟡" if score <= 7 else "🟢")
            with st.expander(f"{icon} {item.get('manufacturer')} {item.get('model_number')}"):
                st.write(f"**Strategy:** {item.get('replace_vs_repair')}")
                if st.button(f"Diagnose {item.get('model_number')}", key=item.get('model_number')):
                    st.session_state.current_asset = item
                    st.session_state.messages = [{"role": "assistant", "content": f"Opening diagnostic records for your {item.get('manufacturer')}. What's happening with it?"}]
                    st.session_state.chat_mode = True
                    st.rerun()
