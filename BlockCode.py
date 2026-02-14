import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --- 1. GEHIRN DER APP (SESSION STATE) ---
# WICHTIG: Hier werden die Schubladen für die Fotos erstellt
if 'foto1_data' not in st.session_state:
    st.session_state.foto1_data = None
if 'foto2_data' not in st.session_state:
    st.session_state.foto2_data = None
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# --- 2. PREIS-ABFRAGE ---
def get_live_prices():
    """Nutzt Punkte statt Kommas und trennt Einträge mit Komma"""
    prices = {
        "Gold": 136.0, 
        "Silber": 1.60, 
        "Kupfer": 0.009, 
        "Nickel": 0.015, 
        "Messing": 0.006, 
        "Zink": 0.003,
        "Stahl": 0.001,
        "source": "Schätzwerte"
    }
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res_g = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAU-EUR=X", headers=headers, timeout=5).json()
        prices["Gold"] = round(res_g['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        res_s = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAG-EUR=X", headers=headers, timeout=5).json()
        prices["Silber"] = round(res_s['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        prices["source"] = "Yahoo Finance Live 📈"
    except:
        pass
    return prices

# --- 3. HILFSFUNKTIONEN ---
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def optimiere_bild(upload_file):
    img = Image.open(upload_file)
    img.thumbnail((1024, 1024))
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=80)
    return buffer.getvalue()

def analysiere_muenze_profi(img1_bytes, img2_bytes, zustand):
    b64_1 = base64.b64encode(img1_bytes).decode('utf-8')
    b64_2 = base64.b64encode(img2_bytes).decode('utf-8')
    headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
    prompt = f"Identifiziere diese Münze. Zustand: {zustand}. Antworte als JSON: {{'name': '...', 'jahr': '...', 'land': '...', 'metall': 'Gold/Silber/Kupfer', 'reinheit': 0.9, 'gewicht': 15.0, 'marktwert_num': 500.0, 'besonderheiten': '...', 'info': '...'}}"
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_1}"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_2}"}}]}],
        "response_format": { "type": "json_object" }
    }
    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 4. APP NAVIGATION ---
st.set_page_config(page_title="Papas Münz-Archiv", layout="centered")

if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-ARCHIV")
    p = get_live_prices()
    st.markdown(f'<div style="background:#ffc107;padding:15px;border-radius:15px;text-align:center;font-weight:bold;">{p["source"]}<br>Gold: {p["Gold"]}€/g | Silber: {p["Silber"]}€/g</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📸 SCANNER", type="primary"):
            st.session_state.page = 'scanner'; st.rerun()
    with col2:
        if st.button("📚 SAMMLUNG"):
            st.session_state.page = 'sammlung'; st.rerun()

elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'; st.rerun()
    
    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    u1 = st.file_uploader("📸 VORDERSEITE", type=["jpg","jpeg","png"], key="c1")
    if u1:
        st.session_state.foto1_data = optimiere_bild(u1)
        st.success("Vorderseite OK! ✅")

    u2 = st.file_uploader("📸 RÜCKSEITE", type=["jpg","jpeg","png"], key="c2")
    if u2:
        st.session_state.foto2_data = optimiere_bild(u2)
        st.success("Rückseite OK! ✅")

    # Sicherer Zugriff mit .get() verhindert Absturz
    if st.session_state.get('foto1_data') and st.session_state.get('foto2_data'):
        if st.button("ANALYSE STARTEN ✨", type="primary"):
            with st.spinner("Experte prüft..."):
                try:
                    res = json.loads(analysiere_muenze_profi(st.session_state.foto1_data, st.session_state.foto2_data, zustand))
                    client = init_supabase()
                    client.table("muenzen").insert({
                        "name": res['name'], "jahr": str(res['jahr']), "land": res['land'],
                        "metall": res['metall'], "reinheit": res['reinheit'], 
                        "gewicht": res['gewicht'], "groesse": res['groesse'], 
                        "auflage": res['auflage'], "marktwert_num": res['marktwert_num'],
                        "besonderheiten": res['besonderheiten'], "info": res['info']
                    }).execute()
                    st.balloons()
                    st.success(f"Gefunden: {res['name']}")
                    st.session_state.foto1_data = None
                    st.session_state.foto2_data = None
                except Exception as e:
                    st.error(f"Fehler: {e}")
    else:
        st.info("Bitte nimm erst beide Fotos auf.")

elif st.session_state.page == 'sammlung':
    # WICHTIG: Alle Zeilen hier MÜSSEN gleich weit eingerückt sein!
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    
    st.title("📚 Deine Sammlung")
    p = get_live_prices()
    try:
        client = init_supabase()
        db_res = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        
        if db_res.data:
            all_metals = sorted(list(set([m['metall'] for m in db_res.data])))
            selected = st.multiselect("Filter:", options=all_metals, default=all_metals)
            filtered = [m for m in db_res.data if m['metall'] in selected]
            
            total_mat, total_hand = 0, 0
            for m in filtered:
                kurs = p.get(m['metall'], 0.001)
                total_mat += (m['gewicht'] or 0) * (m['reinheit'] or 0) * kurs
                total_hand += (m['marktwert_num'] or 0)

            st.markdown(f'<div style="background:#f0f2f6;padding:15px;border-radius:15px;border:2px solid #007bff;"><b>Material: {total_mat:.2f}€ | Handel: {total_hand:.2f}€</b></div>', unsafe_allow_html=True)

            for m in filtered:
                with st.expander(f"🪙 {m['name']} ({m['jahr']})"):
                    st.write(f"Handelswert: {m['marktwert_num']}€")
                    if st.button("🗑️ Löschen", key=f"del_{m['id']}"):
                        client.table("muenzen").delete().eq("id", m['id']).execute()
                        st.rerun()
        else:
            st.info("Noch keine Münzen im Archiv.")
    except Exception as e:
        st.error(f"Datenbankfehler: {e}")
