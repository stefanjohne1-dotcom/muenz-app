import streamlit as st
import requests
import base64
import json
import io
from PIL import Image
from supabase import create_client, Client

# --- 1. VERBINDUNGEN ---
@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_live_prices():
    """Holt Preise für Edelmetalle und nutzt Schätzwerte für unedle Metalle"""
    # Standard-Preise (Euro pro Gramm)
    prices = {
        "Gold": 74.50, 
        "Silber": 0.95, 
        "Kupfer": 0.008, 
        "Nickel": 0.015, 
        "Messing": 0.005, 
        "Zink": 0.003,
        "Unedel": 0.001,
        "source": "Schätzwerte (Offline)"
    }
    
    try:
        # Versuch, Live-Gold/Silber über Yahoo zu laden (Key-frei)
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Gold
        res_g = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F", headers=headers, timeout=5).json()
        prices["Gold"] = round(res_g['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        # Silber
        res_s = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/SI=F", headers=headers, timeout=5).json()
        prices["Silber"] = round(res_s['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
        prices["source"] = "Yahoo Finance Live"
    except:
        pass
    return prices

# --- 2. HILFSFUNKTIONEN ---
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
    prompt = f"""
    Identifiziere diese Münze präzise. Zustand: {zustand}.
    Antworte NUR als JSON:
    {{
      "name": "Name der Münze", "jahr": "Jahr", "land": "Land",
      "metall": "Gold oder Silber oder Kupfer oder Nickel oder Messing", 
      "reinheit": 0.900,
      "gewicht": 15.55, "groesse": "28mm", "auflage": "100.000",
      "marktwert_num": 850, "besonderheiten": "Keine", "info": "Historie..."
    }}
    """
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_1}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_2}"}}
        ]}],
        "response_format": { "type": "json_object" }
    }
    res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return res.json()['choices'][0]['message']['content']

# --- 3. APP SETUP ---
st.set_page_config(page_title="Papas Münz-Archiv", layout="centered")
if 'page' not in st.session_state: st.session_state.page = 'home'

# --- STARTSEITE ---
if st.session_state.page == 'home':
    st.title("🪙 PAPAS MÜNZ-ARCHIV")
    p = get_live_prices()
    st.markdown(f"""
    <div style="background:#ffc107;padding:15px;border-radius:15px;text-align:center;color:#333;border:2px solid #e0a800;">
        <b>{p['source']}</b><br>
        Gold: {p['Gold']}€/g | Silber: {p['Silber']}€/g
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📸 SCANNER", type="primary"):
            st.session_state.page = 'scanner'; st.rerun()
    with col2:
        if st.button("📚 SAMMLUNG"):
            st.session_state.page = 'sammlung'; st.rerun()

# --- SCANNER ---
elif st.session_state.page == 'scanner':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    zst = st.select_slider("Zustand:", options=["Gebraucht", "Normal", "Sehr gut", "Neuwertig"])
    f1 = st.file_uploader("1. Vorderseite", type=["jpg","jpeg","png"])
    f2 = st.file_uploader("2. Rückseite", type=["jpg","jpeg","png"])
    
    if f1 and f2:
        if st.button("ANALYSE STARTEN ✨", type="primary"):
            with st.spinner("Experte prüft..."):
                try:
                    res = json.loads(analysiere_muenze_profi(optimiere_bild(f1), optimiere_bild(f2), zst))
                    client = init_supabase()
                    client.table("muenzen").insert({
                        "name": res['name'], "jahr": str(res['jahr']), "land": res['land'],
                        "metall": res['metall'], "reinheit": res['reinheit'], 
                        "gewicht": res['gewicht'], "groesse": res['groesse'], 
                        "auflage": res['auflage'], "marktwert_num": res['marktwert_num'],
                        "besonderheiten": res['besonderheiten'], "info": res['info']
                    }).execute()
                    st.balloons()
                    st.success(f"Erfolgreich: {res['name']}")
                except Exception as e: st.error(f"Fehler: {e}")

# --- SAMMLUNG ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
       st.title("📚 Deine Sammlung")
    
       p = get_live_prices()
    try:
        client = init_supabase()
        db_res = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        
        if db_res.data:
            # --- FILTER ---
            all_metals = sorted(list(set([m['metall'] for m in db_res.data])))
            selected_metals = st.multiselect("Filter nach Metallart:", options=all_metals, default=all_metals)
            
            # Daten filtern
            filtered_data = [m for m in db_res.data if m['metall'] in selected_metals]
            
            # --- GESAMTWERT BERECHNEN ---
            total_metal = 0
            total_market = 0
            for m in filtered_data:
                kurs = p.get(m['metall'], 0)
                total_metal += (m['gewicht'] or 0) * (m['reinheit'] or 0) * kurs
                total_market += (m['marktwert_num'] or 0)
            
            # Display Gesamtwert
            st.markdown(f"""
            <div style="background:#f0f2f6; padding:15px; border-radius:15px; margin-bottom:20px; border:2px solid #007bff;">
                <h3 style="margin:0; text-align:center;">💰 WERTE ({len(filtered_data)} Münzen)</h3>
                <table style="width:100%; margin-top:10px;">
                    <tr><td>Gesamt Materialwert:</td><td style="text-align:right; font-weight:bold;">{total_metal:.2f}€</td></tr>
                    <tr><td>Gesamt Handelswert:</td><td style="text-align:right; font-weight:bold; color:#007bff;">{total_market:.2f}€</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

            # Einzelne Münzen anzeigen
            for m in filtered_data:
                with st.expander(f"🪙 {m['name']} ({m['jahr']}) - {m['marktwert_num']}€"):
                    kurs = p.get(m['metall'], 0)
                    m_wert = (m['gewicht'] or 0) * (m['reinheit'] or 0) * kurs
                    
                    st.write(f"**Materialwert:** {m_wert:.2f}€ | **Handelswert:** {m['marktwert_num']}€")
                    st.write(f"**Details:** {m['metall']} | {m['gewicht']}g | Auflage: {m['auflage']}")
                    st.write(f"**Besonderheit:** {m['besonderheiten']}")
                    st.info(f"**Info:** {m['info']}")
                    
                    if st.button("🗑️ Löschen", key=f"del_{m['id']}"):
                        client.table("muenzen").delete().eq("id", m['id']).execute()
                        st.rerun()
        else:
st.info("Noch keine Münzen gespeichert.")
    except Exception as e: st.error(f"Fehler: {e}")






