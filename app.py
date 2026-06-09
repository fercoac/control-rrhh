import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
import requests
import time
import base64
import os
import io

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# --- DISEÑO ---
custom_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;}
    .main { background-color: #f8fafc; }
    div.stButton > button {
        width: 100%; border-radius: 12px; height: 3.8em; 
        background-color: #ffffff; color: #1e293b; 
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        transition: all 0.2s ease; font-weight: 600; text-align: left; padding-left: 20px;
    }
    div.stButton > button:hover { border-color: #3b82f6; color: #3b82f6; transform: translateY(-2px); }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 2px solid #3b82f6; padding: 15px; border-radius: 12px; }
    [data-testid="stMetricValue"] { color: #1e3a8a !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #475569 !important; font-weight: 700 !important; }
    thead tr th { background-color: #1e293b !important; color: white !important; font-weight: bold !important; }
    </style>
    """
st.markdown(custom_style, unsafe_allow_html=True)

# --- LOGO ---
if os.path.exists("logo.png"):
    with open("logo.png", "rb") as f:
        data = f.read()
        bin_str = base64.b64encode(data).decode()
    st.markdown(f'<div style="position:fixed;top:20px;right:20px;z-index:1000;"><img src="data:image/png;base64,{bin_str}" width="80" style="opacity:0.9;"></div>', unsafe_allow_html=True)

# --- CONFIGURACIÓN DE DATOS ---
URL_MACRO = "https://script.google.com/macros/s/AKfycby42PKm1KqL0IaqAKfumxB_9_856yueCpJOWx1ersgmb218g6R3sU0Y0SKRQ-ZIQ4Fj/exec"
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"
GID_MARCAS = "598259224"
GID_SOLICITUDES = "0"
GID_FERIADOS = "320254015" 

# --- FUNCIONES ---
def numero_a_letras(n):
    d = {1:"UNO",2:"DOS",3:"TRES",4:"CUATRO",5:"CINCO",6:"SEIS",7:"SIETE",8:"OCHO",9:"NUEVE",10:"DIEZ",11:"ONCE",12:"DOCE",13:"TRECE",14:"CATORCE",15:"QUINCE",16:"DIECISEIS",17:"DIECISIETE",18:"DIECIOCHO",19:"DIECINUEVE",20:"VEINTE",21:"VEINTIUNO",22:"VEINTIDOS",23:"VEINTITRES",24:"VEINTICUATRO",25:"VEINTICINCO",26:"VEINTISEIS",27:"VEINTISIETE",28:"VEINTIOCHO",29:"VEINTINUEVE",30:"TREINTA"}
    return d.get(n, str(n))

@st.cache_data(ttl=300)
def leer_hoja_cache(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    for _ in range(5):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200: return pd.read_csv(io.StringIO(res.text))
        except: time.sleep(1)
    return pd.read_csv(url)

def enviar_correo(dest, sub, body):
    rem = "fercoac@gmail.com"
    pas = "wqhosrswlhrssqrp"
    msg = MIMEText(body); msg['Subject'] = sub; msg['From'] = f"Parque Automotor <{rem}>"; msg['To'] = dest
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(rem, pas); server.sendmail(rem, dest, msg.as_string()); server.quit()
        return True
    except: return False

# --- SESIÓN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'view' not in st.session_state: st.session_state.view = "Home"
if 'role' not in st.session_state: st.session_state.role = "Agente"

# --- LOGIN ---
if not st.session_state.auth:
    st.title("🔐 Control de Ingresos")
    dni_i = st.text_input("DNI")
    pin_i = st.text_input("PIN (4 dígitos)", type="password")
    if st.button("Ingresar"):
        try:
            df = leer_hoja_cache(GID_EMPLEADOS)
            df.columns = df.columns.str.strip()
            df['DNI'] = df['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
            df['PIN'] = df['PIN'].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(4)
            u = df[(df['DNI'] == str(dni_i).strip()) & (df['PIN'] == str(pin_i).strip())]
            if not u.empty:
                st.session_state.auth = True
                st.session_state.user = u.iloc[0].to_dict()
                # DEFINICIÓN DE ROLES
                if str(dni_i).strip() == "28748288": st.session_state.role = "Admin"
                elif str(dni_i).strip() == "29409713": st.session_state.role = "Auditoria"
                else: st.session_state.role = "Agente"
                st.cache_data.clear(); st.rerun()
            else: st.error("DNI o PIN incorrectos.")
        except: st.error("Error de conexión.")

# --- APP ---
else:
    user = st.session_state.user
    role = st.session_state.role
    st.sidebar.write(f"Conectado: **{user['Nombre']}**")
    st.sidebar.caption(f"Perfil: {role}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False; st.session_state.role = "Agente"; st.cache_data.clear(); st.rerun()

    if st.session_state.view == "Home":
        nombre_pila = user['Nombre'].split()[-1]
        st.title(f"Hola, {nombre_pila} 👋")
        
        # MENÚ SEGÚN ROL
        if role == "Auditoria":
            if st.button("🚨 Auditoría: Control de Tardanzas"): st.session_state.view = "AuditoriaTardanzas"; st.rerun()
            if st.button("🔍 Auditoría: Revisar Solicitudes"): st.session_state.view = "AuditoriaSolicitudes"; st.rerun()
        
        if role != "Auditoria": # Botones normales para Agentes y Admin
            if st.button("📋 Mis Marcas Biométricas"): st.session_state.view = "Marcas"; st.rerun()
            if st.button("🏖️ Solicitar Licencia LAR"): st.session_state.view = "Vacaciones"; st.rerun()
            if st.button("📄 Solicitar Art. 74 (Particulares)"): st.session_state.view = "Art74"; st.rerun()
            if st.button("🔍 Ver Mis Solicitudes"): st.session_state.view = "Historial"; st.rerun()

        if role == "Admin":
            st.divider()
            if st.button("🚨 PANEL CONTROL ADMIN"): st.session_state.view = "AdminTardanzas"; st.rerun()

    # --- VISTAS AUDITORÍA ---
    elif st.session_state.view == "AuditoriaTardanzas":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("📊 Fiscalización de Tardanzas")
        
        tab_act, tab_ant, tab_custom = st.tabs(["Mes Actual", "Mes Anterior", "📅 Rango Personalizado"])
        
        df_all = leer_hoja_cache(GID_MARCAS); df_all.columns = df_all.columns.str.strip()
        df_all['temp_f'] = pd.to_datetime(df_all['Fecha'], dayfirst=True)
        df_all['temp_h'] = pd.to_datetime(df_all['Hora'], format='%H:%M').dt.time
        lim_i, lim_f = datetime.strptime("08:11", "%H:%M").time(), datetime.strptime("09:00", "%H:%M").time()

        def rep_auditoria(df_filtrado):
            t = df_filtrado[(df_filtrado['temp_h'] >= lim_i) & (df_filtrado['temp_h'] <= lim_f) & (df_filtrado['Evento'].str.strip().isin(['Entrada', 'Acceso']))].copy()
            if not t.empty:
                for ag in sorted(t['Nombre'].unique()):
                    df_ag = t[t['Nombre'] == ag].sort_values('temp_f', ascending=False)
                    with st.expander(f"📌 {ag} ({len(df_ag.drop_duplicates(subset=['Fecha']))} tardanzas)"):
                        st.dataframe(df_ag[['Fecha', 'Hora', 'Evento']], use_container_width=True, hide_index=True)
            else: st.info("Sin registros de tardanza en este periodo.")

        with tab_act:
            rep_auditoria(df_all[(df_all['temp_f'].dt.month == datetime.now().month) & (df_all['temp_f'].dt.year == datetime.now().year)])
        with tab_ant:
            ant = datetime.now().replace(day=1) - timedelta(days=1)
            rep_auditoria(df_all[(df_all['temp_f'].dt.month == ant.month) & (df_all['temp_f'].dt.year == ant.year)])
        with tab_custom:
            r = st.date_input("Seleccione rango:", value=(date.today()-timedelta(days=7), date.today()), format="DD/MM/YYYY")
            if isinstance(r, tuple) and len(r) == 2:
                rep_auditoria(df_all[(df_all['temp_f'].dt.date >= r[0]) & (df_all['temp_f'].dt.date <= r[1])])

    elif st.session_state.view == "AuditoriaSolicitudes":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("📋 Monitor de Solicitudes (Personal)")
        
        df_sol = leer_hoja_cache(GID_SOLICITUDES)
        filtro = st.radio("Filtrar por estado:", ["Todas", "Pendiente", "Aprobado", "Rechazado"], horizontal=True)
        
        if filtro != "Todas":
            df_sol = df_sol[df_sol['Estado'].str.strip() == filtro]
        
        def fmt_est(v):
            if v == "Aprobado": return "✅ Aprobado"
            if v == "Pendiente": return "⏳ Pendiente"
            return "❌ Rechazado" if v == "Rechazado" else v
            
        df_sol['Estado'] = df_sol['Estado'].apply(fmt_est)
        st.dataframe(df_sol[['Nombre', 'Tipo', 'Fecha_Inicio', 'Fecha_Fin', 'Estado']], use_container_width=True, hide_index=True)

    # --- VISTAS NORMALES ---
    elif st.session_state.view == "Marcas":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("📋 Mis Registros")
        df = leer_hoja_cache(GID_MARCAS); df.columns = df.columns.str.strip()
        mi_id = str(int(float(user['ID_Biometrico'])))
        col_id = df.columns[0]
        df[col_id] = df[col_id].astype(str).str.strip().str.replace('.0', '', regex=False)
        m = df[df[col_id] == mi_id].copy()
        if not m.empty:
            m['temp_f'] = pd.to_datetime(m['Fecha'], dayfirst=True)
            m['temp_h'] = pd.to_datetime(m['Hora'], format='%H:%M').dt.time
            h_ini = date.today() - timedelta(days=7)
            r = st.date_input("Rango:", value=(h_ini, date.today()), format="DD/MM/YYYY")
            if isinstance(r, tuple) and len(r) == 2:
                m_f = m[(m['temp_f'].dt.date >= r[0]) & (m['temp_f'].dt.date <= r[1])].copy()
            else: m_f = m.copy()
            m_o = m.sort_values(by=['temp_f', 'temp_h'], ascending=False)
            st.success(f"Último: {m_o.iloc[0]['Evento']} el {m_o.iloc[0]['Fecha']}")
            st.dataframe(m_f.drop(columns=['temp_f', 'temp_h']), use_container_width=True, hide_index=True)
        else: st.info("Sin registros.")

    elif st.session_state.view == "Vacaciones":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("🏖️ Solicitar LAR")
        try:
            df_sol = leer_hoja_cache(GID_SOLICITUDES); df_sol.columns = df_sol.columns.str.strip()
            dni_u = str(user['DNI']).split('.')[0]
            mis_lar = df_sol[(df_sol['DNI'].astype(str) == dni_u) & (df_sol['Tipo'] == 'LAR')]
            rem = float(user['Dias_Totales']) - mis_lar['Dias_Habiles'].sum()
            st.metric("Días LAR Disponibles", f"{int(rem)}")
            if len(mis_lar) >= 2: st.error("Límite alcanzado.")
            else:
                f_i = st.date_input("Inicio", format="DD/MM/YYYY")
                f_f = st.date_input("Fin", min_value=f_i, format="DD/MM/YYYY")
                try:
                    df_f = leer_hoja_cache(GID_FERIADOS)
                    l_f = set(pd.to_datetime(df_f['Fecha'], dayfirst=True, errors='coerce').dropna().dt.date.tolist())
                except: l_f = set()
                d_p = len([f_i+timedelta(days=i) for i in range((f_f-f_i).days+1) if (f_i+timedelta(days=i)).weekday()<5 and (f_i+timedelta(days=i)) not in l_f])
                if d_p > 0:
                    st.info(f"Días: {d_p} | Saldo final: {int(rem-d_p)}")
                    if rem >= d_p and st.checkbox("Confirmo fechas"):
                        if st.button("🚀 ENVIAR"):
                            p = {"dni": dni_u, "nombre": user['Nombre'], "inicio": f_i.strftime('%d/%m/%Y'), "fin": f_f.strftime('%d/%m/%Y'), "dias": d_p, "tipo": "LAR"}
                            if requests.post(URL_MACRO, json=p).status_code == 200:
                                st.success("✅ Solicitud Realizada")
                                hoy = datetime.now(); meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                                dias_s = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                                f_hoy_l = f"{dias_s[hoy.weekday()]} {hoy.day} de {meses[hoy.month-1]} de {hoy.year}"
                                n_let = numero_a_letras(d_p)
                                nota = f"SOLICITUD DE LICENCIA\nSALTA, {f_hoy_l}\n\nPor la presente solicito la concesión de LICENCIA ANUAL ORDINARIA/2025 a partir del \ndía: {f_i.strftime('%d/%m/%Y')}, hasta el día {f_f.strftime('%d/%m/%Y')} inclusive, por el termino de {d_p} ({n_let}) días hábiles.\n\n\n.....................................             .....................................\n       V°B° del Jefe                             Firma del solicitante"
                                st.text_area("Copia para imprimir:", nota, height=350)
                                enviar_correo("rrhhparqueautomotor@gmail.com", f"LAR: {user['Nombre']}", nota)
                                st.cache_data.clear()
        except: st.error("Error.")

    elif st.session_state.view == "Art74":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("📄 Artículo 74")
        try:
            df_sol = leer_hoja_cache(GID_SOLICITUDES)
            dni_u = str(user['DNI']).split('.')[0]
            u_art = len(df_sol[(df_sol['DNI'].astype(str) == dni_u) & (df_sol['Tipo'] == 'Art74')])
            st.metric("Días Art. 74 Disponibles", f"{2 - u_art}")
            if u_art < 2:
                f_art = st.date_input("Fecha", format="DD/MM/YYYY")
                if st.button("🚀 ENVIAR ART. 74"):
                    p = {"dni": dni_u, "nombre": user['Nombre'], "inicio": f_art.strftime('%d/%m/%Y'), "fin": f_art.strftime('%d/%m/%Y'), "dias": 1, "tipo": "Art74"}
                    if requests.post(URL_MACRO, json=p).status_code == 200:
                        st.success("✅ Solicitud Realizada")
                        hoy = datetime.now()
                        nota_art = f"SOLICITUD ART. 74\nSALTA, {hoy.strftime('%d/%m/%Y')}\n\nYo {user['Nombre']}, solicito Art. 74 para el día {f_art.strftime('%d/%m/%Y')}.\n\n...................\nFirma"
                        st.text_area("Copia:", nota_art, height=300)
                        enviar_correo("rrhhparqueautomotor@gmail.com", f"ART 74: {user['Nombre']}", nota_art)
                        st.cache_data.clear()
        except: st.error("Error.")

    elif st.session_state.view == "Historial":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("🔍 Mis Solicitudes")
        try:
            df_sol = leer_hoja_cache(GID_SOLICITUDES)
            dni_u = str(user['DNI']).split('.')[0]
            mis_s = df_sol[df_sol['DNI'].astype(str) == dni_u].copy()
            if not mis_s.empty:
                def fmt(v):
                    if str(v).strip() == "Aprobado": return "✅ Aprobado"
                    if str(v).strip() == "Pendiente": return "⏳ Pendiente"
                    return "❌ Rechazado" if str(v).strip() == "Rechazado" else v
                mis_s['Estado'] = mis_s['Estado'].apply(fmt)
                st.dataframe(mis_s[['Tipo', 'Fecha_Inicio', 'Fecha_Fin', 'Dias_Habiles', 'Estado']], use_container_width=True, hide_index=True)
            else: st.info("Sin registros.")
        except: st.error("Error.")

    elif st.session_state.view == "Feriados":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("🗓️ Feriados")
        df_f = leer_hoja_cache(GID_FERIADOS); st.dataframe(df_f, use_container_width=True, hide_index=True)

    elif st.session_state.view == "AdminTardanzas":
        if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
        st.header("🚨 Reporte Admin")
        tab_ac, tab_an = st.tabs(["Mes en Curso", "Mes Anterior"])
        df_all = leer_hoja_cache(GID_MARCAS); df_all.columns = df_all.columns.str.strip()
        df_all['temp_f'] = pd.to_datetime(df_all['Fecha'], dayfirst=True)
        df_all['temp_h'] = pd.to_datetime(df_all['Hora'], format='%H:%M').dt.time
        hoy = datetime.now(); ant = hoy.replace(day=1) - timedelta(days=1)
        lim_i, lim_f = datetime.strptime("08:11", "%H:%M").time(), datetime.strptime("09:00", "%H:%M").time()
        def rep(m, a):
            t = df_all[(df_all['temp_f'].dt.month == m) & (df_all['temp_f'].dt.year == a) & (df_all['temp_h'] >= lim_i) & (df_all['temp_h'] <= lim_f) & (df_all['Evento'].str.strip().isin(['Entrada', 'Acceso']))].copy()
            if not t.empty:
                for ag in sorted(t['Nombre'].unique()):
                    df_ag = t[t['Nombre'] == ag].sort_values('temp_f', ascending=False)
                    st.markdown(f"### **{ag}**")
                    st.write(f"Tardanzas: {len(df_ag.drop_duplicates(subset=['Fecha']))}")
                    st.dataframe(df_ag[['Fecha', 'Hora', 'Evento']], use_container_width=True, hide_index=True)
                    st.divider()
            else: st.info("Sin registros.")
        with tab_ac: rep(hoy.month, hoy.year)
        with tab_an: rep(ant.month, ant.year)
