import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# --- DISEÑO PROFESIONAL DE BOTONES Y OCULTAR MENÚS ---
custom_style = """
    <style>
    /* Ocultar menús de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;}

    /* Estilo para los botones de la Home */
    div.stButton > button {
        width: 100%;
        border-radius: 15px;
        height: 3.5em;
        background-color: #ffffff;
        color: #1f1f1f;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        font-weight: 600;
        font-size: 16px;
    }

    /* Efecto al pasar el mouse */
    div.stButton > button:hover {
        border-color: #3d5afe;
        color: #3d5afe;
        transform: translateY(-3px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.15);
    }

    /* Efecto al hacer clic */
    div.stButton > button:active {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    </style>
    """
st.markdown(custom_style, unsafe_allow_html=True)

# --- CONFIGURACIÓN DE DATOS ---
URL_MACRO = "https://script.google.com/macros/s/AKfycby42PKm1KqL0IaqAKfumxB_9_856yueCpJOWx1ersgmb218g6R3sU0Y0SKRQ-ZIQ4Fj/exec"
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"
GID_MARCAS = "598259224"
GID_SOLICITUDES = "0"
GID_FERIADOS = "320254015" 

# --- FUNCIONES ---
def leer_hoja(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    for i in range(3):
        try: return pd.read_csv(url)
        except: time.sleep(1)
    return pd.read_csv(url)

def enviar_correo(destinatario, asunto, cuerpo):
    remitente = "fercoac@gmail.com"
    password = "wqhosrswlhrssqrp" 
    msg = MIMEText(cuerpo)
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        return True
    except: return False

# --- SESIÓN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'view' not in st.session_state: st.session_state.view = "Home"

# --- LOGIN ---
if not st.session_state.auth:
    st.title("🔐 Control de Ingresos")
    dni_i = st.text_input("DNI")
    pin_i = st.text_input("PIN", type="password")
    if st.button("Ingresar"):
        try:
            df = leer_hoja(GID_EMPLEADOS)
            df.columns = df.columns.str.strip()
            df['DNI'] = df['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
            df['PIN'] = df['PIN'].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(4)
            u = df[(df['DNI'] == str(dni_i).strip()) & (df['PIN'] == str(pin_i).strip())]
            if not u.empty:
                st.session_state.auth = True
                st.session_state.user = u.iloc[0].to_dict()
                st.rerun()
            else: st.error("DNI o PIN incorrectos")
        except: st.error("Error de conexión.")

# --- APP ---
else:
    user = st.session_state.user
    st.sidebar.write(f"**{user['Nombre']}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

    if st.session_state.view == "Home":
        st.title(f"Hola, {user['Nombre'].split()[0]} 👋")
        st.write("Selecciona una opción:")
        
        # Botones con estilo personalizado
        if st.button("📋 Ver Mis Marcas"):
            st.session_state.view = "Marcas"
            st.rerun()
        
        if st.button("🏖️ Solicitar Vacaciones (LAR)"):
            st.session_state.view = "Vacaciones"
            st.rerun()
            
        if st.button("📄 Solicitar Art. 74 (Razones Particulares)"):
            st.session_state.view = "Art74"
            st.rerun()

    elif st.session_state.view == "Marcas":
        if st.button("⬅️ Volver al Inicio"): st.session_state.view = "Home"; st.rerun()
        st.header("📋 Mis Registros")
        df = leer_hoja(GID_MARCAS)
        df.columns = df.columns.str.strip()
        mi_id = str(int(float(user['ID_Biometrico'])))
        col_id = df.columns[0]
        df[col_id] = df[col_id].astype(str).str.strip().str.replace('.0', '', regex=False)
        m = df[df[col_id] == mi_id].copy()
        if not m.empty:
            m['dt'] = pd.to_datetime(m['Fecha'] + ' ' + m['Hora'], dayfirst=True)
            st.dataframe(m.sort_values('dt', ascending=False).drop(columns=['dt']), use_container_width=True, hide_index=True)
        else: st.info("Sin registros")

    elif st.session_state.view == "Vacaciones":
        if st.button("⬅️ Volver al Inicio"): st.session_state.view = "Home"; st.rerun()
        st.header("🏖️ Solicitud LAR")
        
        try:
            df_sol = leer_hoja(GID_SOLICITUDES)
            df_sol.columns = df_sol.columns.str.strip()
            dni_u = str(user['DNI']).split('.')[0]
            mis_lar = df_sol[(df_sol['DNI'].astype(str) == dni_u) & (df_sol['Tipo'] == 'LAR')]
            usados = mis_lar['Dias_Habiles'].sum()
        except: usados = 0
        
        rem = float(user['Dias_Totales']) - usados
        st.metric("Días LAR Disponibles", f"{int(rem)}")
        
        # Cargar feriados para cálculo
        try:
            url_fer = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_FERIADOS}"
            df_fer = pd.read_csv(url_fer)
            f_s = pd.to_datetime(df_fer['Fecha'], dayfirst=True, errors='coerce')
            l_fer = set(f_s.dropna().dt.date.tolist())
        except: l_fer = set()

        f_i = st.date_input("Inicio", format="DD/MM/YYYY")
        f_f = st.date_input("Fin", min_value=f_i, format="DD/MM/YYYY")
        
        c_d = (f_f - f_i).days + 1
        d_h = [f_i + timedelta(days=i) for i in range(c_d) if (f_i + timedelta(days=i)).weekday() < 5 and (f_i + timedelta(days=i)) not in l_fer]
        pedidos = len(d_h)
        
        if pedidos > 0:
            st.info(f"Días a solicitar: {pedidos}")
            if rem >= pedidos:
                if st.checkbox("Confirmo fechas"):
                    if st.button("🚀 ENVIAR SOLICITUD LAR"):
                        p = {"dni": str(user['DNI']).split('.')[0], "nombre": user['Nombre'], "inicio": f_i.strftime('%d/%m/%Y'), "fin": f_f.strftime('%d/%m/%Y'), "dias": pedidos, "tipo": "LAR"}
                        requests.post(URL_MACRO, json=p)
                        st.success("Enviado")

    elif st.session_state.view == "Art74":
        if st.button("⬅️ Volver al Inicio"): st.session_state.view = "Home"; st.rerun()
        st.header("📄 Artículo 74")
        
        try:
            df_sol = leer_hoja(GID_SOLICITUDES)
            df_sol.columns = df_sol.columns.str.strip()
            dni_u = str(user['DNI']).split('.')[0]
            mis_art = df_sol[(df_sol['DNI'].astype(str) == dni_u) & (df_sol['Tipo'] == 'Art74')]
            usados_art = len(mis_art)
        except: usados_art = 0
        
        disp = 2 - usados_art
        st.metric("Art. 74 Disponibles", f"{disp}")
        
        if disp > 0:
            f_art = st.date_input("Día solicitado", format="DD/MM/YYYY")
            if st.button("🚀 ENVIAR ART. 74"):
                p = {"dni": str(user['DNI']).split('.')[0], "nombre": user['Nombre'], "inicio": f_art.strftime('%d/%m/%Y'), "fin": f_art.strftime('%d/%m/%Y'), "dias": 1, "tipo": "Art74"}
                res = requests.post(URL_MACRO, json=p)
                if res.status_code == 200:
                    st.success("Enviado")
                    # (Aquí va la lógica de la nota y mail igual que antes)
        else: st.error("Sin días disponibles")
