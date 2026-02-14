import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --- 1. INITIALISIERUNG (ERWEITERT UM ANALYSIS_RESULT) ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'foto1' not in st.session_state: st.session_state.foto1 = None
if 'foto2' not in st.session_state: st.session_state.foto2 = None
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None

# --- 2. PREISE (LIVE & ALLE METALLE) ---
def get_live_prices():
    p = {
        "Gold": 135.9, "Silber": 1.59, "Kupfer": 0.009, 
        "Nickel": 0.015, "Messing": 0.006, "Zink": 0.003,
        "Stahl": 0.001, "Eisen": 0.001, "source": "Schätzwerte"
    }
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        res_g = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAU-EUR=X", headers=h, timeout=5).json()
        p["Gold"] = round(res_g['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        res_s = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAG-EUR=X", headers=h, timeout=5).json()
        p["Silber"] = round(res_s['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        p["source"] = "Yahoo Live 📈"
    except: pass
    return p

# --- 3. HILFSFUNKTIONEN ---
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def optimiere(file):
    img = Image.open(file)
    img.thumbnail((800, 800))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=75)
    return buf.getvalue()

def analysiere_ki(f1, f2, zustand):
    b1 = base64.b64encode(f1).decode()
    b2 = base64.b64encode(f2).decode()
    headers = {"Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}"}
    prompt = f"""Identifiziere diese Münze präzise. Zustand: {zustand}. Antworte NUR als JSON:
    {{'name': '...', 'jahr': '...', 'land': '...', 'metall': 'Gold/Silber/Kupfer/Nickel/Messing/Zink/Stahl/Eisen', 
    'reinheit': 0.9, 'gewicht': 15.55, 'groesse': '28mm', 'auflage': '100.000', 'marktwert_num': 850.0, 
    'besonderheiten': '...', 'info': '...'}}"""
    
    payload = {
        "model": "gpt-4o-mini", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b1}"}},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b2}"}}]}],
        "response_format": { "type": "json_object" }
    }
    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 4. APP DESIGN ---
st.set_page_config(page_title="Münz-Archiv", layout="centered")

# --- HOME ---
if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-ARCHIV")
    p = get_live_prices()
    st.markdown(f'<div style="background:#ffc107;padding:15px;border-radius:15px;text-align:center;color:#333;"><b>{p["source"]}</b><br>Gold: {p["Gold"]}€/g | Silber: {p["Silber"]}€/g</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
            st.session_state.foto1 = None; st.session_state.foto2 = None
            st.session_state.analysis_result = None
            st.session_state.page = 'scanner'; st.rerun()
    with col2:
        if st.button("📚 SAMMLUNG"):
            st.session_state.page = 'sammlung'; st.rerun()

# --- SCANNER MIT BESTÄTIGUNG ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ABBRECHEN"): st.session_state.page = 'home'; st.rerun()
    
    # SCHRITT A: FOTOS AUFNEHMEN (Nur wenn noch keine Analyse da ist)
    if st.session_state.analysis_result is None:
        st.subheader("Fotos aufnehmen")
        zst = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
        
        c1 = st.camera_input("1. VORDERSEITE")
        if c1: st.session_state.foto1 = optimiere(c1)
        
        if st.session_state.foto1:
            st.success("Vorderseite gespeichert! ✅")
            c2 = st.camera_input("2. RÜCKSEITE")
            if c2: st.session_state.foto2 = optimiere(c2)

        if st.session_state.foto1 and st.session_state.foto2:
            if st.button("ANALYSE STARTEN ✨", type="primary"):
                with st.spinner("KI wertet aus..."):
                    res_raw = analysiere_ki(st.session_state.foto1, st.session_state.foto2, zst)
                    st.session_state.analysis_result = json.loads(res_raw)
                    st.rerun()
    
    # SCHRITT B: BESTÄTIGUNG DER KI-ERGEBNISSE
    else:
        res = st.session_state.analysis_result
        p = get_live_prices()
        k = p.get(res['metall'], 0.001)
        m_w = float(res['gewicht']) * float(res['reinheit']) * k
        
        st.warning("⚠️ Bitte überprüfe die KI-Analyse:")
        
        st.markdown(f"""
        <div style="background:white; padding:20px; border-radius:15px; border:2px solid #ffd700; color:#333;">
            <h3 style="margin-top:0;">{res['name']} ({res['jahr']})</h3>
            <p><b>Land:</b> {res['land']} | <b>Material:</b> {res['metall']}</p>
            <hr>
            <p>📈 <b>Berechneter Materialwert: {m_w:.2f}€</b></p>
            <p>💰 <b>Geschätzter Handelswert: {res['marktwert_num']}€</b></p>
            <hr>
            <p>⚖️ <b>Gewicht:</b> {res['gewicht']}g | 📏 <b>Größe:</b> {res['groesse']}</p>
            <p>📉 <b>Auflage:</b> {res['auflage']}</p>
            <p>🌟 <b>Besonderheit:</b> {res['besonderheiten']}</p>
            <p style="font-style:italic; color:#555;">{res['info']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_ok, col_no = st.columns(2)
        with col_ok:
            if st.button("✅ STIMMT, AB INS ARCHIV", type="primary"):
                with st.spinner("Speichere..."):
                    client = init_supabase()
                    client.table("muenzen").insert({
                        "name": res['name'], "jahr": str(res['jahr']), "land": res['land'], 
                        "metall": res['metall'], "reinheit": res['reinheit'], "gewicht": res['gewicht'],
                        "groesse": res['groesse'], "auflage": res['auflage'], 
                        "marktwert_num": res['marktwert_num'], "besonderheiten": res['besonderheiten'], "info": res['info']
                    }).execute()
                    st.balloons()
                    st.session_state.analysis_result = None
                    st.session_state.page = 'sammlung'; st.rerun()
        
        with col_no:
            if st.button("❌ FALSCH, NEU SCANNEN"):
                st.session_state.analysis_result = None
                st.session_state.foto1 = None; st.session_state.foto2 = None
                st.rerun()

# --- SAMMLUNG ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    st.title("📚 Sammlung")
    p = get_live_prices()
    
    try:
        client = init_supabase()
        db = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        
        if db.data:
            all_m = sorted(list(set([m['metall'] for m in db.data])))
            selected = st.multiselect("Filtern nach Metall:", options=all_m, default=all_m)
            filtered = [m for m in db.data if m['metall'] in selected]
            
            t_mat, t_hand = 0, 0
            for m in filtered:
                k = p.get(m['metall'], 0.001)
                t_mat += (m['gewicht'] or 0) * (m['reinheit'] or 0) * k
                t_hand += (m['marktwert_num'] or 0)

            st.markdown(f"""<div style="background:#f0f2f6;padding:20px;border-radius:15px;border:2px solid #007bff;">
                <h3 style="margin:0;text-align:center;">GESAMTWERT</h3>
                <table style="width:100%;margin-top:10px;">
                    <tr><td>Materialwert:</td><td style="text-align:right;"><b>{t_mat:.2f}€</b></td></tr>
                    <tr><td>Handelswert:</td><td style="text-align:right;color:#007bff;"><b>{t_hand:.2f}€</b></td></tr>
                </table></div>""", unsafe_allow_html=True)

            for m in filtered:
                with st.expander(f"🪙 {m['name']} ({m['jahr']})"):
                    k = p.get(m['metall'], 0.001)
                    m_w = (m['gewicht'] or 0) * (m['reinheit'] or 0) * k
                    st.write(f"**Material:** {m_w:.2f}€ | **Handel:** {m['marktwert_num']}€")
                    st.write(f"**Daten:** {m['metall']} | {m['gewicht']}g | {m['groesse']} | Auflage: {m['auflage']}")
                    st.write(f"**Besonderheit:** {m['besonderheiten']}")
                    st.info(m['info'])
                    if st.button("🗑️ Löschen", key=f"del_{m['id']}"):
                        client.table("muenzen").delete().eq("id", m['id']).execute(); st.rerun()
        else: st.info("Archiv ist noch leer.")
    except Exception as e: st.error(f"Fehler: {e}")

