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
    # Standardwerte (Punkte statt Kommas nutzen!)
    p = {
        "Gold": 135.9, "Silber": 1.6, "Kupfer": 0.009, 
        "Nickel": 0.015, "Messing": 0.006, "Zink": 0.003,
        "Stahl": 0.001, "Eisen": 0.001, "source": "Schätzwerte"
    }
    try:
        h = {'User-Agent': 'Mozilla/5.0'}
        # Gold-Abfrage
        res_g = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAU-EUR=X", headers=h, timeout=5).json()
        # Prüfen, ob die Daten-Struktur wirklich existiert (verhindert NoneType-Fehler)
        if res_g and 'chart' in res_g and res_g['chart']['result']:
            p["Gold"] = round(res_g['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
            
        # Silber-Abfrage
        res_s = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/XAG-EUR=X", headers=h, timeout=5).json()
        if res_s and 'chart' in res_s and res_s['chart']['result']:
            p["Silber"] = round(res_s['chart']['result'][0]['meta']['regularMarketPrice'] / 31.1035, 2)
            p["source"] = "Yahoo Live 📈"
    except Exception:
        # Falls irgendwas schiefgeht, bleiben einfach die Schätzwerte stehen
        pass
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
    
    # Der "strenge" Experten-Prompt:
    prompt = f"""
    Du bist ein numismatischer Sachverständiger und Experte für Edelmetallmünzen. Identifiziere diese Münze.
    
    OBERSTE REGEL (EXTREM WICHTIG, NICHT IGNORIEREN!):
    Lese den Nennwert (z.B. "11 Euro", "25 Euro" EXAKT von den Bildern ab. VERBOTEN: Rate nicht aufgrund von Standardwerten! Wenn dort eine "11" steht, musst du diesen WERT ("11") akzeptieren, auch wenn "10" üblicher wäre.
    
    REGELN ZUR LOGIK-WARNUNG (SEHR LOCKER):
    1. PRÄGEJAHR-CHECK: Das Jahr ist dein wichtigster Parameter.
    2. LOGIK-ABGLEICH: Gleiche das Prägejahr zwingend mit den Symbolen/Wappen ab. 
       Beispiel: Ein Jahr von 1950 passt nicht zu einem Kaiser-Porträt oder Wappen des 19. Jahrhunderts.
    3. WICHTIG: MODERNE SONDERMÜNZEN (ab 2000) haben oft ungewöhnliche Nennwerte (wie z.B. 11 Euro z.B. Deutschland 2024, 25 Euro oder andere ungewöhnliche Gedenkmünzen-Werte. Das ist KORREKT und KEIN Fehler!
    4. Nur wenn das Jahr absolut NICHT zur Epoche passt (z.B. Jahr 2024 bei einem Kaiserreich-Adler oder Eisernes Kreuz), beginne den "name" mit dem Wort "FEHLER:".

    WICHTIG FÜR DIE WERTERMITTLUNG:
    1. Ermittle das EXAKTE Gewicht, die EXAKTE Reinheit (Feingehalt), die EXAKTE Auflage (wie viele Münzen wurden im Prägejahr geprägt), die EXAKTE groesse und den Marktwert aus dem Durchschnittspreis der letzten zehn von Dir gefundenen Verkäufe dieser Münze.
    2. Verwende NIEMALS die Platzhalterwerte 15.55, 0.9, Durchmesser in mm, Auflagenzahl und 0.0. Wenn die Münze (z.B. 11 Euro von 2024) 14g wiegt und 500er Silber (0.5) ist, MUSST du 14.0 und 0.5 angeben.
    
    Zustand: {zustand}.
    Antworte NUR als JSON:
    {{
      "name": "Vollständiger Name der Münze",
      "jahr": "Gefundenes Prägejahr",
      "land": "Land",
      "metall": "Gold/Silber/Kupfer/Nickel/Messing/Zink/Stahl/Eisen/Aluminium", 
      "reinheit": 0.0, 
      "gewicht": 0.0, 
      "groesse": "Durchmesser in mm", 
      "auflage": "Auflagenzahl", 
      "marktwert_num": 0.0, 
      "besonderheiten": "Begründung der Logikprüfung (z.B. Warum das Nominal zum Jahr passt)", 
      "info": "Historischer Kontext, Sind Fehlprägungen bekannt? (3-4 Sätze)"
    }}
    """
    
    payload = {
        "model": "gpt-4o-mini", 
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b1}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b2}"}}
        ]}],
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
            <h1 style="color: #333; margin: 0;">Papas Münz-APP</h1>
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
        u2 = st.file_uploader("2. RÜCKSEITE einfügen", type=["jpg", "jpeg", "png"], key="u2")
        if u2: st.session_state.foto2 = optimiere(u2)

        if st.session_state.foto1 and st.session_state.foto2:
            st.divider()
            if st.button("ANALYSE STARTEN ✨", type="primary"):
                with st.spinner("KI prüft Logik von Jahr und Wappen..."):
                    res_raw = analysiere_ki(st.session_state.foto1, st.session_state.foto2, zst)
                    st.session_state.analysis_result = json.loads(res_raw)
                    st.rerun()
    
    else:
        res = st.session_state.analysis_result
        p = get_live_prices()
        
        st.warning("📊 Daten prüfen & ggf. korrigieren:")
        
        # --- MANUELLE KORREKTUR-ZEILE ---
        c_ed1, c_ed2, c_ed3 = st.columns(3)
        with c_ed1:
            neu_jahr = st.text_input("Jahr:", value=res['jahr'])
        with c_ed2:
            # Hier kann Papa das Gewicht korrigieren (z.B. auf 14.0)
            neu_gew = st.number_input("Gewicht (g):", value=reinige_zahl(res['gewicht']), step=0.01)
        with c_ed3:
            # Hier die Reinheit (z.B. auf 0.5 für 500er Silber)
            neu_rein = st.number_input("Reinheit (0.1-1.0):", value=reinige_zahl(res['reinheit']), step=0.01)

        freigabe = st.checkbox("Daten manuell geprüft & freigeben")
        
        # Live-Berechnung mit den korrigierten Werten
        kurs = p.get(res['metall'], 0.001)
        m_wert = neu_gew * neu_rein * kurs

        st.markdown(f"""
        <div style="background:white; padding:15px; border-radius:15px; border:2px solid #ffd700; color:#333;">
            <h3 style="margin:0;">{res['name']}</h3>
            <p><b>Materialwert aktuell: {m_wert:.2f}€</b></p>
            <p style="font-size:0.8em; color:grey;">(Berechnung: {neu_gew}g x {neu_rein} Reinheit x {kurs}€ Kurs)</p>
            <hr>
            <p><b>Info:</b> {res['info']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if freigabe or ("FEHLER" not in res['name'].upper()):
                if st.button("✅ JETZT SPEICHERN", type="primary"):
                    init_supabase().table("muenzen").insert({
                        "name": res['name'].replace("FEHLER: ", ""), "jahr": str(neu_jahr),
                        "land": res['land'], "metall": res['metall'], "reinheit": neu_rein,
                        "gewicht": neu_gew, "groesse": res['groesse'], "auflage": res['auflage'], 
                        "marktwert_num": reinige_zahl(res['marktwert_num']), 
                        "besonderheiten": res['besonderheiten'], "info": res['info']
                    }).execute()
                    st.balloons(); st.session_state.analysis_result = None; st.session_state.page = 'sammlung'; st.rerun()
            else:
                st.button("🚫 FREIGABE FEHLT", disabled=True)
        with c2:
            if st.button("❌ VERWERFEN"): st.session_state.analysis_result = None; st.rerun()

# --- 4. SEITE: SAMMLUNG (MIT KORRIGIERTEM DESIGN & LOGIK) ---
elif st.session_state.page == 'sammlung':
    if st.button("⬅️ ZURÜCK"): st.session_state.page = 'home'; st.rerun()
    
    st.markdown("""
        <div style="background-color: #ffd700; padding: 10px; border-radius: 10px; text-align: center;">
            <h1 style="color: #333; margin: 0;">📚 DEINE SAMMLUNG</h1>
        </div><br>
    """, unsafe_allow_html=True)
    
    p = get_live_prices()
    try:
        client = init_supabase()
        db = client.table("muenzen").select("*").order("created_at", desc=True).execute()
        
        # LOGIK-FIX: Wir prüfen erst, ob ÜBERHAUPT Daten da sind
        if db.data and len(db.data) > 0:
            metals = sorted(list(set([m['metall'] for m in db.data])))
            sel = st.multiselect("Filtern nach Metall:", options=metals, default=metals)
            filtered = [m for m in db.data if m['metall'] in sel]
            
            t_mat, t_hand = 0, 0
            for m in filtered:
                k = p.get(m['metall'], 0.001)
                t_mat += (m['gewicht'] or 0) * (m['reinheit'] or 0) * k
                t_hand += (m['marktwert_num'] or 0)

            # DESIGN-FIX: Dunkler Hintergrund für bessere Lesbarkeit
            st.markdown(f"""
                <div style="background-color: #1e3a8a; padding: 25px; border-radius: 15px; border: 2px solid #ffd700; color: white; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                    <h3 style="margin: 0; color: #ffd700;">GESAMTWERT</h3>
                    <hr style="border-color: rgba(255,255,255,0.2);">
                    <table style="width: 100%; color: white; font-size: 1.1em;">
                        <tr>
                            <td style="text-align: left;">Materialwert (Schmelz):</td>
                            <td style="text-align: right;"><b>{t_mat:.2f}€</b></td>
                        </tr>
                        <tr>
                            <td style="text-align: left; color: #ffd700;">Handelswert (Markt):</td>
                            <td style="text-align: right; color: #ffd700;"><b>{t_hand:.2f}€</b></td>
                        </tr>
                    </table>
                </div><br>
            """, unsafe_allow_html=True)

            # Münz-Liste
            for m in filtered:
                with st.expander(f"🪙 {m['name']} ({m['jahr']})"):
                    st.write(f"**Material:** {((m['gewicht'] or 0)*(m['reinheit'] or 0)*p.get(m['metall'], 0)):.2f}€ | **Handel:** {m['marktwert_num']}€")
                    st.write(f"**Details:** {m['gewicht']}g | {m['metall']} ({m['reinheit']})")
                    if st.button("🗑️ Löschen", key=f"del_{m['id']}"):
                        client.table("muenzen").delete().eq("id", m['id']).execute(); st.rerun()
        
        # Die Meldung erscheint jetzt NUR, wenn db.data wirklich leer ist
        else:
st.info("Das Archiv ist aktuell noch leer. Scanne deine erste Münze!")
            
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")














