import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# --- DISEÑO PROFESIONAL MEJORADO ---
custom_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;}

    /* Botones Home con sombra y color sutil */
    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #ffffff;
        color: #1f1f1f;
        border: 1px solid #d1d5db;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
        font-weight: 600;
    }
    div.stButton > button:hover {
        border-color: #2563eb;
        color: #2563eb;
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    /* Estilo para las métricas */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #2563eb;
    }
    </style>
    """
st.markdown(custom_style, unsafe_allow_html=True)

# --- DATOS DE CONEXIÓN ---
URL_MACRO = "https://script.google.com/macros/s/AKfycby42PKm1KqL0IaqAKfumxB_9_856yueCpJOWx1ersgmb218g6R3sU0Y0SKRQ-ZIQ4Fj/exec"
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"
GID_MARCAS = "598259224"
GID_SOLICITUDES = "0"
GID_FERIADOS = "320254015" 

# --- FUNCIONES CORE ---
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

# --- GESTIÓN DE SESIÓN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'view' not in st.session_state: st.session_state.view = "Home"

# --- PANTALLA LOGIN ---
if not st.session_state.auth:
    st.title("🔐 Control de Ingresos")
    dni_i = st.text_input("DNI")
    pin_i = st.text_input("PIN (4 dígitos)", type="password")
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

# --- APP PRINCIPAL ---
else:
    user = st.session_state.user
    st.sidebar.write(f"Conectado: **{user['Nombre']}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

    # --- HOME ---
    if st.session_state.view == "Home":
        st.title(f"Hola, {user['Nombre'].split()[0]} 👋")
        st.write("¿Qué necesitas consultar hoy?")
        
        if st.button("📋 Ver Mis Marcas Biométricas"):
            st.session_state.view = "Marcas"; st.rerun()
        
        if st.button("🏖️ Solicitar Licencia LAR"):
            st.session_state.view = "Vacaciones"; st.rerun()
            
        if st.button("📄 Solicitar Art. 74 (Particulares)"):
            st.session_state.view = "Art74"; st.rerun()

        if st.button("🔍 Ver Estado de Mis Solicitudes"):
            st.session_state.view = "Historial"; st.rerun()

    # --- VISTA MARCAS ---
    elif st.session_state.view == "Marcas":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
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
        else: st.info("No hay marcas registradas.")

    # --- VISTA LAR ---
    elif st.session_state.view == "Vacaciones":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("🏖️ Solicitar LAR")
        
        try:
            df_sol = leer_hoja(GID_SOLICITUDES)
            df_sol.columns = df_sol.columns.str.strip()
            dni_u = str(user['DNI']).split('.')[0]
            usados = df_sol[(df_sol['DNI'].astype(str) == dni_u) & (df_sol['Tipo'] == 'LAR')]['Dias_Habiles'].sum()
        except: usados = 0
        
        rem = float(user['Dias_Totales']) - usados
        # BARRA DE PROGRESO
        porcentaje = min(1.0, usados / float(user['Dias_Totales']))
        st.write(f"Días utilizados: {int(usados)} de {int(user['Dias_Totales'])}")
        st.progress(porcentaje)
        st.metric("Días Disponibles", f"{int(rem)}")

        f_i = st.date_input("Fecha Inicio", format="DD/MM/YYYY", min_value=date.today())
        f_f = st.date_input("Fecha Fin", min_value=f_i, format="DD/MM/YYYY")
        
        # Cargar feriados para el cálculo
        try:
            url_f = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_FERIADOS}"
            df_f = pd.read_csv(url_f)
            l_f = set(pd.to_datetime(df_f['Fecha'], dayfirst=True, errors='coerce').dropna().dt.date.tolist())
        except: l_f = set()

        rango = (f_f - f_i).days + 1
        dias_p = len([f_i + timedelta(days=i) for i in range(rango) if (f_i + timedelta(days=i)).weekday() < 5 and (f_i + timedelta(days=i)) not in l_f])

        if dias_p > 0:
            st.info(f"Días hábiles a descontar: {dias_p}")
            if rem >= dias_p:
                if st.checkbox("Confirmo fechas de LAR"):
                    if st.button("🚀 ENVIAR SOLICITUD"):
                        p = {"dni": str(user['DNI']).split('.')[0], "nombre": user['Nombre'], "inicio": f_i.strftime('%d/%m/%Y'), "fin": f_f.strftime('%d/%m/%Y'), "dias": dias_p, "tipo": "LAR"}
                        requests.post(URL_MACRO, json=p)
                        st.success("✅ Solicitud enviada.")

    # --- VISTA ART 74 ---
    elif st.session_state.view == "Art74":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("📄 Artículo 74")
        
        try:
            df_sol = leer_hoja(GID_SOLICITUDES)
            dni_u = str(user['DNI']).split('.')[0]
            usados_art = len(df_sol[(df_sol['DNI'].astype(str) == dni_u) & (df_sol['Tipo'] == 'Art74')])
        except: usados_art = 0
        
        st.write(f"Días utilizados este año: {usados_art} de 2")
        st.progress(usados_art / 2)
        
        if usados_art < 2:
            f_art = st.date_input("Día solicitado", format="DD/MM/YYYY")
            if st.button("🚀 ENVIAR ART. 74"):
                p = {"dni": str(user['DNI']).split('.')[0], "nombre": user['Nombre'], "inicio": f_art.strftime('%d/%m/%Y'), "fin": f_art.strftime('%d/%m/%Y'), "dias": 1, "tipo": "Art74"}
                requests.post(URL_MACRO, json=p)
                st.success("✅ Art. 74 enviado.")
        else: st.error("No tienes más días disponibles de Art. 74.")

    # --- VISTA HISTORIAL ---
    elif st.session_state.view == "Historial":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("🔍 Estado de Mis Solicitudes")
        try:
            df_sol = leer_hoja(GID_SOLICITUDES)
            df_sol.columns = df_sol.columns.str.strip()
            dni_u = str(user['DNI']).split('.')[0]
            mis_s = df_sol[df_sol['DNI'].astype(str) == dni_u].copy()
            if not mis_s.empty:
                # Estilizar el estado
                def color_estado(val):
                    color = '#fef3c7' if val == 'Pendiente' else '#d1fae5'
                    return f'background-color: {color}'
                
                st.write("Aquí puedes ver si tus pedidos ya fueron aprobados por RRHH:")
                st.dataframe(mis_s[['Tipo', 'Fecha_Inicio', 'Fecha_Fin', 'Dias_Habiles', 'Estado']], use_container_width=True, hide_index=True)
            else:
                st.info("No has realizado ninguna solicitud todavía.")
        except:
            st.error("No se pudo cargar el historial.")
