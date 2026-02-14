import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --- 1. DAS GEDÄCHTNIS DER APP (Ganz oben!) ---
# Initialisiert alle Variablen sofort, um AttributeError zu verhindern
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'foto1_data' not in st.session_state: st.session_state.foto1_data = None
if 'foto2_data' not in st.session_state: st.session_state.foto2_data = None

# --- 2. LIVE-PREISE (Yahoo Finance Alternative) ---
def get_live_prices():
    # Saubere Zahlen mit Punkt statt Komma
    prices = {
        "Gold": 136.0, "Silber": 1.61, "Kupfer": 0.009, 
        "Nickel": 0.015, "Messing": 0.006, "Zink": 0.003, "source": "Schätzwerte"
    }
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res_g = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAU-EUR=X", headers=headers, timeout=5).json()
        prices["Gold"] = round(res_g['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        res_s = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAG-EUR=X", headers=headers, timeout=5).json()
        prices["Silber"] = round(res_s['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        prices["source"] = "Yahoo Finance Live 📈"
    except: pass
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
    prompt = f"Identifiziere diese Münze präzise. Zustand: {zustand}. Antworte NUR als JSON: {{'name': '...', 'jahr': '...', 'land': '...', 'metall': 'Gold/Silber/Kupfer/Nickel/Messing/Zink', 'reinheit': 0.9, 'gewicht': 15.55, 'groesse': '28mm', 'auflage': '100.000', 'marktwert_num': 850.0, 'besonderheiten': '...', 'info': '...'}}"
    payload = {
        "model": "gpt-4o-mini", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, 
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_1}"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_2}"}}]}],
        "response_format": { "type": "json_object" }
    }
    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 4. APP NAVIGATION ---
st.set_page_config(page_title="Papas Münz-Archiv", layout="centered")

# SEITE: HOME
if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-ARCHIV")
    p = get_live_prices()
    st.markdown(f'<div style="background:#ffc107;padding:15px;border-radius:15px;text-align:center;font-weight:bold;color:#333;">{p["source"]}<br>Gold: {p["Gold"]}€/g | Silber: {p["Silber"]}€/g</div>', unsafe_allow_html=True)
    
if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
    st.session_state.foto1_data, st.session_state.foto2_data = None, None
    st.session_state.page = 'scanner'; st.rerun()
if st.button("📚 SAMMLUNG & WERTE"):
    st.session_state.page = 'sammlung'; st.rerun()

# SEITE: SCANNER (Memory-Safe Version)
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    
    zustand = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    
    # Der stabilste Weg für Handys: Unabhängige Upload-Felder
    u1 = st.file_uploader("1. VORDERSEITE aufnehmen", type=["jpg","jpeg","png"], key="u1")
    if u1: st.session_state.foto1_data = optimiere_bild(u1)
    if st.session_state.foto1_data: st.success("Vorderseite gespeichert! ✅")

    u2 = st.file_uploader("2. RÜCKSEITE aufnehmen", type=["jpg","jpeg","png"], key="u2")
    if u2: st.session_state.foto2_data = optimiere_bild(u2)
    if st.session_state.foto2_data: st.success("Rückseite gespeichert! ✅")

    if st.session_state.foto1_data and st.session_state.foto2_data:
        if st.button("JETZT ANALYSIEREN ✨", type="primary"):
            with st.spinner("Experte prüft die Bilder..."):
                try:
                    res = json.loads(analysiere_muenze_profi(st.session_state.foto1_data, st.session_state.foto2_data, zustand))
                    client = init_supabase()
                    client.table("muenzen").insert({
                        "name": res['name'], "jahr": str(res['jahr']), "land": res['land'], "metall": res['metall'], 
                        "reinheit": res['reinheit'], "gewicht": res['gewicht'], "groesse": res['groesse'], 
                        "auflage": res['auflage'], "marktwert_num": res['marktwert_num'], "besonderheiten": res['besonderheiten'], "info": res['info']
                    }).execute()
                    st.balloons(); st.success(f"Gefunden: {res['name']}")
                    st.session_state.foto1_data, st.session_state.foto2_data = None, None
                except Exception as e: st.error(f"Fehler: {e}")

# SEITE: SAMMLUNG (Mit Filtern & Gesamtwert)
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
        st.title("📚 Deine Schätze")
    
        p = get_live_prices()
    try:
        client = init_supabase()
        db_res = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        
        if db_res.data:
            metals = sorted(list(set([m['metall'] for m in db_res.data])))
            selected = st.multiselect("Filter nach Metall:", options=metals, default=metals)
            filtered = [m for m in db_res.data if m['metall'] in selected]
            
            t_mat, t_hand = 0, 0
            for m in filtered:
                kurs = p.get(m['metall'], 0.001)
                t_mat += (m['gewicht'] or 0) * (m['reinheit'] or 0) * kurs
                t_hand += (m['marktwert_num'] or 0)

            st.markdown(f"""<div style="background:#f0f2f6;padding:15px;border-radius:15px;margin-bottom:20px;border:2px solid #007bff;">
                <h3 style="margin:0;text-align:center;">GESAMTWERT</h3>
                <table style="width:100%;">
                    <tr><td>Materialwert:</td><td style="text-align:right;"><b>{t_mat:.2f}€</b></td></tr>
                    <tr><td>Handelswert:</td><td style="text-align:right;color:#007bff;"><b>{t_hand:.2f}€</b></td></tr>
                </table></div>""", unsafe_allow_html=True)

            for m in filtered:
                with st.expander(f"🪙 {m['name']} ({m['jahr']})"):
                    st.write(f"Material: {((m['gewicht'] or 0)*(m['reinheit'] or 0)*p.get(m['metall'], 0)):.2f}€ | Handel: {m['marktwert_num']}€")
                    st.write(f"Details: {m['metall']} | {m['gewicht']}g | {m['groesse']} | Auflage: {m['auflage']}")
                    st.info(m['info'])
                    if st.button("🗑️ Löschen", key=f"del_{m['id']}"):
                        client.table("muenzen").delete().eq("id", m['id']).execute(); st.rerun()
else: st.info("Archiv ist noch leer.")
    except Exception as e: st.error(f"Datenbankfehler: {e}")

