import streamlit as st
import requests
import base64
import json
import io
import re
from PIL import Image
from supabase import create_client, Client

# --- 1. INITIALISIERUNG (GEHIRN DER APP) ---
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'foto1' not in st.session_state: st.session_state.foto1 = None
if 'foto2' not in st.session_state: st.session_state.foto2 = None
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None

# --- 2. PREISE (LIVE & ALLE METALLE) ---
def get_live_prices():
    p = {
        "Gold": 135.9, "Silber": 2.1, "Kupfer": 0.009, 
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

def reinige_zahl(text):
    """Extrahiert reine Zahlen aus KI-Texten wie '15,55 g'"""
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
st.set_page_config(page_title="Papas Münz-App", layout="centered")

# --- SEITE: HOME ---
if st.session_state.page == 'home':
    st.markdown("""
        <div style="background-color: #ffd700; padding: 10px; border-radius: 10px; text-align: center;">
            <h1 style="color: #333; margin: 0;">PAPAS MÜNZ-App</h1>
        </div><br>
    """, unsafe_allow_html=True)
    
    p = get_live_prices()
    st.markdown(f'<div style="background:#f0f2f6;padding:15px;border-radius:15px;text-align:center;color:#333;"><b>{p["source"]}</b><br>Gold: {p["Gold"]}€/g | Silber: {p["Silber"]}€/g</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📸 NEUE MÜNZE SCANNEN", type="primary"):
            st.session_state.foto1, st.session_state.foto2 = None, None
            st.session_state.analysis_result = None
            st.session_state.page = 'scanner'; st.rerun()
    with col2:
        if st.button("📚 MEINE SAMMLUNG"):
            st.session_state.page = 'sammlung'; st.rerun()

# --- SEITE: SCANNER (GALERIE-UPLOAD & BESTÄTIGUNG) ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ABBRECHEN"): st.session_state.page = 'home'; st.rerun()
    
    if st.session_state.analysis_result is None:
        st.subheader("Fotos aus Galerie einfügen")
        zst = st.select_slider("Zustand wählen:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
        
        u1 = st.file_uploader("1. VORDERSEITE einfügen", type=["jpg", "jpeg", "png"], key="u1")
        if u1: st.session_state.foto1 = optimiere(u1)
        if st.session_state.foto1: st.success("Vorderseite geladen! ✅")

        u2 = st.file_uploader("2. RÜCKSEITE einfügen", type=["jpg", "jpeg", "png"], key="u2")
        if u2: st.session_state.foto2 = optimiere(u2)
        if st.session_state.foto2: st.success("Rückseite geladen! ✅")

        if st.session_state.foto1 and st.session_state.foto2:
            st.divider()
            if st.button("ANALYSE STARTEN ✨", type="primary"):
                with st.spinner("KI wertet aus..."):
                    try:
                        res_raw = analysiere_ki(st.session_state.foto1, st.session_state.foto2, zst)
                        st.session_state.analysis_result = json.loads(res_raw)
                        st.rerun()
                    except Exception as e: st.error(f"Fehler: {e}")
    
    else:
        res = st.session_state.analysis_result
        p = get_live_prices()
        kurs = p.get(res['metall'], 0.001)
        gew, rein = reinige_zahl(res['gewicht']), reinige_zahl(res['reinheit'])
        m_w = gew * rein * kurs
        
        st.warning("📊 Bitte Analyse bestätigen:")
        st.markdown(f"""
        <div style="background:white; padding:20px; border-radius:15px; border:2px solid #ffd700; color:#333;">
            <h3 style="margin-top:0;">{res['name']} ({res['jahr']})</h3>
            <p>📈 <b>Materialwert: {m_w:.2f}€</b> | 💰 <b>Handelswert: {res['marktwert_num']}€</b></p>
            <hr>
            <p>⚖️ <b>Gewicht:</b> {res['gewicht']}g | 🧪 <b>Metall:</b> {res['metall']} ({rein*1000:.0f}/1000)</p>
            <p>📉 <b>Auflage:</b> {res['auflage']} | 📏 <b>Größe:</b> {res['groesse']}</p>
            <p>🌟 <b>Besonderheit:</b> {res['besonderheiten']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_ok, col_no = st.columns(2)
        with col_ok:
            if st.button("✅ SPEICHERN", type="primary"):
                init_supabase().table("muenzen").insert({
                    "name": res['name'], "jahr": str(res['jahr']), "land": res['land'], 
                    "metall": res['metall'], "reinheit": rein, "gewicht": gew,
                    "groesse": res['groesse'], "auflage": res['auflage'], 
                    "marktwert_num": reinige_zahl(res['marktwert_num']), 
                    "besonderheiten": res['besonderheiten'], "info": res['info']
                }).execute()
                st.balloons(); st.session_state.analysis_result = None; st.session_state.page = 'sammlung'; st.rerun()
        with col_no:
            if st.button("❌ ABBRECHEN"):
                st.session_state.analysis_result = None; st.rerun()

# --- SEITE: SAMMLUNG (MIT ALLEN DETAILS) ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"):
        st.session_state.page = 'home'
        st.rerun()
    
    st.markdown("""
        <div style="background-color: #ffd700; padding: 10px; border-radius: 10px; text-align: center;">
            <h1 style="color: #333; margin: 0;">📚 DEINE SAMMLUNG</h1>
        </div><br>
    """, unsafe_allow_html=True)
    
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
                    <tr><td>Materialwert (Schmelzwert):</td><td style="text-align:right;"><b>{t_mat:.2f}€</b></td></tr>
                    <tr><td>Handelswert (Marktwert):</td><td style="text-align:right;color:#007bff;"><b>{t_hand:.2f}€</b></td></tr>
                </table></div>""", unsafe_allow_html=True)

            for m in filtered:
                # Expander zeigt alle Zusatzinfos an
                with st.expander(f"🪙 {m['name']} ({m['jahr']})"):
                    k = p.get(m['metall'], 0.001)
                    m_w = (m['gewicht'] or 0) * (m['reinheit'] or 0) * k
                    
                    st.write(f"**Land:** {m['land']}")
                    st.write(f"**Materialwert:** {m_w:.2f}€ | **Handelswert:** {m['marktwert_num']}€")
                    st.write(f"**Technische Daten:** {m['metall']} | {m['gewicht']}g | {m['groesse']}")
                    st.write(f"**Auflage:** {m['auflage']}")
                    st.write(f"**Besonderheiten:** {m['besonderheiten']}")
                    st.info(f"**Hintergrund-Info:** {m['info']}")
                    
                    if st.button("🗑️ Löschen", key=f"del_{m['id']}"):
                        client.table("muenzen").delete().eq("id", m['id']).execute(); st.rerun()
            else:
                st.info("Archiv ist noch leer.")
    except Exception as e:
        st.error(f"Datenbankfehler: {e}")


