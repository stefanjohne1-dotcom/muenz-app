import streamlit as st
import requests
import base64
import json
import io
import re
from PIL import Image
from supabase import create_client, Client

# --- 1. INITIALISIERUNG ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'foto1' not in st.session_state: st.session_state.foto1 = None
if 'foto2' not in st.session_state: st.session_state.foto2 = None
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None

# --- 2. PREISE (LIVE & FALLBACK) ---
def get_live_prices():
    p = {
        "Gold": 135.9, "Silber": 1.6, "Kupfer": 0.009, 
        "Nickel": 0.015, "Messing": 0.006, "Zink": 0.003,
        "Stahl": 0.001, "Eisen": 0.001, "source": "Schätzwerte"
    }
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        res_g = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAU-EUR=X", headers=h, timeout=5).json()
        p["Gold"] = round(res_g['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        res_s = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAG-EUR=X", headers=h, timeout=5).json()
        p["Silber"] = round(res_s['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        p["source"] = "Live-Kurse 📈"
    except: pass
    return p

# --- 3. HILFSFUNKTIONEN ---
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def reinige_zahl(text):
    """Macht aus '15,55 g' ein sauberes 15.55"""
    if isinstance(text, (int, float)): return float(text)
    match = re.search(r"[-+]?\d*\.?\d+", str(text).replace(",", "."))
    return float(match.group()) if match else 0.0

def optimiere(file):
    img = Image.open(file)
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=80)
    return buf.getvalue()

def analysiere_ki(f1, f2, zustand):
    b1 = base64.b64encode(f1).decode(); b2 = base64.b64encode(f2).decode()
    headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
    prompt = f"Identifiziere diese Münze ({zustand}). Antworte NUR als JSON: {{'name': '...', 'jahr': '...', 'land': '...', 'metall': 'Gold/Silber/Kupfer/Nickel/Messing/Zink/Stahl/Eisen', 'reinheit': 0.9, 'gewicht': 15.55, 'groesse': '28mm', 'auflage': '100.000', 'marktwert_num': 850.0, 'besonderheiten': '...', 'info': '...'}}"
    payload = {
        "model": "gpt-4o-mini", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b1}"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b2}"}}]}],
        "response_format": { "type": "json_object" }
    }
    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 4. NAVIGATION ---
st.set_page_config(page_title="PAPAS Münz-App", layout="centered")

if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-App")
    p = get_live_prices()
    st.info(f"{p['source']} - Gold: {p['Gold']}€/g | Silber: {p['Silber']}€/g")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📸 NEUE MÜNZE", type="primary"):
            st.session_state.foto1 = None; st.session_state.foto2 = None
            st.session_state.analysis_result = None
            st.session_state.page = 'scanner'; st.rerun()
    with col2:
        if st.button("📚 SAMMLUNG"): st.session_state.page = 'sammlung'; st.rerun()

elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    
    if st.session_state.analysis_result is None:
        zst = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
        u1 = st.file_uploader("1. Vorderseite", type=["jpg", "png"], key="u1")
        if u1: st.session_state.foto1 = optimiere(u1)
        u2 = st.file_uploader("2. Rückseite", type=["jpg", "png"], key="u2")
        if u2: st.session_state.foto2 = optimiere(u2)

        if st.session_state.foto1 and st.session_state.foto2:
            if st.button("ANALYSE STARTEN ✨", type="primary"):
                with st.spinner("KI arbeitet..."):
                    res_raw = analysiere_ki(st.session_state.foto1, st.session_state.foto2, zst)
                    st.session_state.analysis_result = json.loads(res_raw); st.rerun()
    else:
        res = st.session_state.analysis_result
        p = get_live_prices()
        kurs = p.get(res['metall'], 0.001)
        gewicht = reinige_zahl(res['gewicht'])
        reinheit = reinige_zahl(res['reinheit'])
        m_wert = gewicht * reinheit * kurs
        
        st.warning("🔍 Bitte bestätigen:")
        st.write(f"### {res['name']} ({res['jahr']})")
        st.write(f"**Materialwert:** {m_wert:.2f}€ | **Sammlerwert:** {res['marktwert_num']}€")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ SPEICHERN", type="primary"):
                init_supabase().table("muenzen").insert({
                    "name": res['name'], "jahr": str(res['jahr']), "land": res['land'], 
                    "metall": res['metall'], "reinheit": reinheit, "gewicht": gewicht,
                    "groesse": res['groesse'], "auflage": res['auflage'], 
                    "marktwert_num": reinige_zahl(res['marktwert_num']), 
                    "besonderheiten": res['besonderheiten'], "info": res['info']
                }).execute()
                st.balloons(); st.session_state.analysis_result = None; st.session_state.page = 'sammlung'; st.rerun()
        with c2:
            if st.button("❌ VERWERFEN"): st.session_state.analysis_result = None; st.rerun()

elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    st.title("📚 Deine Sammlung")
    p = get_live_prices()
    try:
        db = init_supabase().table("muenzen").select("*").order("created_at", desc=True).execute()
        if db.data:
            metals = sorted(list(set([m['metall'] for m in db.data])))
            sel = st.multiselect("Filter:", options=metals, default=metals)
            filtered = [m for m in db.data if m['metall'] in sel]
            
            t_mat, t_hand = 0, 0
            for m in filtered:
                k = p.get(m['metall'], 0.001)
                t_mat += (m['gewicht'] or 0) * (m['reinheit'] or 0) * k
                t_hand += (m['marktwert_num'] or 0)

            st.success(f"Gesamt Material: {t_mat:.2f}€ | Handel: {t_hand:.2f}€")
            for m in filtered:
                with st.expander(f"🪙 {m['name']} ({m['jahr']})"):
                    st.write(f"Handelswert: {m['marktwert_num']}€")
                    if st.button("🗑️ Löschen", key=f"del_{m['id']}"):
                        init_supabase().table("muenzen").delete().eq("id", m['id']).execute(); st.rerun()
        else: st.info("Archiv leer.")
    except Exception as e: st.error(f"Fehler: {e}")

