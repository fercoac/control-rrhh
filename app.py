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
st.set_page_config(page_title="RRHH - Parque Automotor", layout="wide", initial_sidebar_state="collapsed")

# --- FUNCIONES AUXILIARES ---
def numero_a_letras(n):
    d = {1:"UNO",2:"DOS",3:"TRES",4:"CUATRO",5:"CINCO",6:"SEIS",7:"SIETE",8:"OCHO",9:"NUEVE",10:"DIEZ",11:"ONCE",12:"DOCE",13:"TRECE",14:"CATORCE",15:"QUINCE",16:"DIECISEIS",17:"DIECISIETE",18:"DIECIOCHO",19:"DIECINUEVE",20:"VEINTE",21:"VEINTIUNO",22:"VEINTIDOS",23:"VEINTITRES",24:"VEINTICUATRO",25:"VEINTICINCO",26:"VEINTISEIS",27:"VEINTISIETE",28:"VEINTIOCHO",29:"VEINTINUEVE",30:"TREINTA"}
    return d.get(n, str(n))

def get_base64(bin_file):
    with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()

def set_logo():
    if os.path.exists("logo.png"):
        bin_str = get_base64("logo.png")
        st.markdown(f'<div style="position:fixed;top:20px;right:25px;z-index:1000;"><img src="data:image/png;base64,{bin_str}" width="85"></div>', unsafe_allow_html=True)

set_logo()

# --- DISEÑO CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;} [data-testid="stSidebarNav"] {display: none;}
    .main { background-color: #f8fafc; }
    div.stButton > button {
        width: 100%; border-radius: 12px; height: 3.8em; background-color: #ffffff; color: #1e293b; 
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        transition: all 0.2s ease; font-weight: 700; text-align: left; padding-left: 20px;
    }
    div.stButton > button:hover { border-color: #2563eb; color: #2563eb; transform: translateY(-2px); }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 2px solid #2563eb; padding: 15px; border-radius: 12px; }
    [data-testid="stMetricValue"] { color: #1e3a8a !important; font-weight: 800 !important; font-size: 2.2rem !important; }
    [data-testid="stMetricLabel"] { color: #475569 !important; font-weight: 700 !important; }
    thead tr th { background-color: #0f172a !important; color: white !important; font-weight: bold !important; }
    .metric-box-audit { background-color: #ffffff; padding: 15px; border-radius: 12px; border-left: 5px solid #2563eb; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- DATOS ---
URL_MACRO = "https://script.google.com/macros/s/AKfycby42PKm1KqL0IaqAKfumxB_9_856yueCpJOWx1ersgmb218g6R3sU0Y0SKRQ-ZIQ4Fj/exec"
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"; GID_MARCAS = "598259224"; GID_SOLICITUDES = "0"; GID_FERIADOS = "320254015" 

@st.cache_data(ttl=60)
def leer_hoja_cache(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    headers = {"User-Agent": "Mozilla/5.0"}
    for _ in range(5):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return pd.read_csv(io.StringIO(res.content.decode('utf-8'))).drop_duplicates()
        except: time.sleep(1)
    return pd.DataFrame()

def enviar_correo(dest, sub, body):
    try:
        s = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        s.login("fercoac@gmail.com", "wqhosrswlhrssqrp")
        msg = MIMEText(body); msg['Subject'] = sub; msg['From'] = "RRHH Parque Automotor <fercoac@gmail.com>"; msg['To'] = dest
        s.sendmail("fercoac@gmail.com", dest, msg.as_string()); s.quit()
        return True
    except: return False

# --- SESIÓN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'view' not in st.session_state: st.session_state.view = "Home"
if 'role' not in st.session_state: st.session_state.role = "User"

# --- LOGIN ---
if not st.session_state.auth:
    st.title("🔐 Acceso al Sistema")
    st.caption("Subsecretaría del Parque Automotor")
    dni_i = st.text_input("DNI")
    pin_i = st.text_input("PIN (4 dígitos)", type="password")
    if st.button("Ingresar"):
        df_e = leer_hoja_cache(GID_EMPLEADOS)
        if not df_e.empty:
            df_e.columns = df_e.columns.str.strip()
            df_e['DNI'] = df_e['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
            df_e['PIN'] = df_e['PIN'].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(4)
            u = df_e[(df_e['DNI'] == str(dni_i).strip()) & (df_e['PIN'] == str(pin_i).strip())]
            if not u.empty:
                st.session_state.auth = True
                st.session_state.user = u.iloc[0].to_dict()
                if dni_i == "29409713": st.session_state.role = "Auditor"; st.session_state.view = "AuditoriaTardanzas"
                elif dni_i == "28748288": st.session_state.role = "Admin"
                st.cache_data.clear(); st.rerun()
            else: st.error("Credenciales incorrectas")

# --- APP AUTENTICADA ---
else:
    user = st.session_state.user
    # Sidebar común para todos
    st.sidebar.subheader("👤 Perfil")
    st.sidebar.write(f"**{user['Nombre']}**")
    st.sidebar.caption(f"Rol: {st.session_state.role}")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False; st.session_state.role = "User"; st.session_state.view = "Home"; st.rerun()

    # ==========================================
    # PERFIL AUDITORÍA (PATRICIA)
    # ==========================================
    if st.session_state.role == "Auditor":
        st.markdown(f"### 📑 Panel de Auditoría Interna")
        c1, c2, c3 = st.columns(3)
        with c1: 
            if st.button("⏰ Control Tardanzas"): st.session_state.view = "AuditoriaTardanzas"; st.rerun()
        with c2: 
            if st.button("📂 Control Licencias"): st.session_state.view = "AuditoriaLicencias"; st.rerun()
        with c3: 
            if st.button("🚪 Salir Seguro"): st.session_state.auth = False; st.rerun()
        st.divider()

        if st.session_state.view == "AuditoriaTardanzas":
            t_act, t_ant = st.tabs(["📊 Mes en Curso", "📊 Mes Anterior"])
            df_m = leer_hoja_cache(GID_MARCAS)
            df_m.columns = df_m.columns.str.strip()
            df_m['temp_f'] = pd.to_datetime(df_m['Fecha'], dayfirst=True)
            df_m['temp_h'] = pd.to_datetime(df_m['Hora'], format='%H:%M').dt.time
            hoy = datetime.now(); ant = hoy.replace(day=1) - timedelta(days=1)
            lim_i, lim_f = datetime.strptime("08:11", "%H:%M").time(), datetime.strptime("09:00", "%H:%M").time()

            def render_audit_tardanzas(m, a):
                t = df_m[(df_m['temp_f'].dt.month == m) & (df_m['temp_f'].dt.year == a) & (df_m['temp_h'] >= lim_i) & (df_m['temp_h'] <= lim_f) & (df_m['Evento'].str.strip().isin(['Entrada', 'Acceso']))].copy()
                if not t.empty:
                    agentes = t['Nombre'].unique()
                    st.markdown(f'<div class="metric-box-audit">Agentes con tardanzas: <b>{len(agentes)}</b> | Total marcas: <b>{len(t)}</b></div>', unsafe_allow_html=True)
                    for ag in sorted(agentes):
                        df_ag = t[t['Nombre'] == ag].sort_values('temp_f', ascending=False)
                        with st.expander(f"🚩 {ag} - Total: {len(df_ag)}"):
                            st.dataframe(df_ag[['Fecha', 'Hora', 'Evento']], use_container_width=True, hide_index=True)
                            if st.button(f"Notificar a {ag.split()[0]}", key=f"not_{ag}_{m}"):
                                enviar_correo("rrhhparqueautomotor@gmail.com", f"Apercibimiento - {ag}", f"Auditoría registra {len(df_ag)} tardanzas en el periodo {m}/{a} para {ag}.")
                                st.success("Aviso enviado")
                else: st.info("Sin tardanzas registradas.")
            with t_act: render_audit_tardanzas(hoy.month, hoy.year)
            with t_ant: render_audit_tardanzas(ant.month, ant.year)

        elif st.session_state.view == "AuditoriaLicencias":
            st.subheader("📂 Fichaje General de Licencias")
            df_s = leer_hoja_cache(GID_SOLICITUDES); df_s.columns = df_s.columns.str.strip()
            cf1, cf2, cf3 = st.columns([1,1,2])
            with cf1: tip = st.selectbox("Tipo:", ["Todas", "LAR", "Art74"])
            with cf2: est = st.selectbox("Estado:", ["Todos", "Pendiente", "Aprobado", "Rechazado"])
            with cf3: bus = st.text_input("Buscar por Nombre/DNI:")
            res = df_s.copy()
            if tip != "Todas": res = res[res['Tipo'] == tip]
            if est != "Todos": res = res[res['Estado'] == est]
            if bus: res = res[res['Nombre'].str.contains(bus, case=False) | res['DNI'].astype(str).str.contains(bus)]
            st.dataframe(res, use_container_width=True, hide_index=True)
            st.divider()
            st.subheader("🗓️ Auditoría de Disponibilidad Diaria")
            d_aud = st.date_input("Ver agentes de licencia el día:", value=date.today())
            def is_lic(row, d):
                try:
                    i = datetime.strptime(row['Fecha_Inicio'], '%d/%m/%Y').date()
                    f = datetime.strptime(row['Fecha_Fin'], '%d/%m/%Y').date()
                    return i <= d <= f and row['Estado'] == 'Aprobado'
                except: return False
            ina = df_s[df_s.apply(lambda r: is_lic(r, d_aud), axis=1)]
            if not ina.empty:
                for _, r in ina.iterrows(): st.warning(f"🚫 **{r['Nombre']}** ({r['Tipo']}) - Hasta: {r['Fecha_Fin']}")
            else: st.success("Plantilla completa para este día.")

    # ==========================================
    # PERFIL AGENTE / ADMIN (GUIDO Y OTROS)
    # ==========================================
    else:
        if st.session_state.view == "Home":
            nombre_pila = user['Nombre'].split()[-1]
            st.title(f"Hola, {nombre_pila} 👋")
            st.write("¿Qué deseas realizar hoy?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 Mis Marcas Biométricas"): st.session_state.view = "Marcas"; st.rerun()
                if st.button("🏖️ Solicitar Licencia LAR"): st.session_state.view = "Vacaciones"; st.rerun()
            with col2:
                if st.button("📄 Solicitar Art. 74"): st.session_state.view = "Art74"; st.rerun()
                if st.button("🔍 Mis Solicitudes"): st.session_state.view = "Historial"; st.rerun()
            if st.button("🗓️ Consultar Feriados"): st.session_state.view = "Feriados"; st.rerun()
            if st.session_state.role == "Admin":
                st.divider()
                if st.button("🚨 PANEL CONTROL ADMIN"): st.session_state.view = "AdminTardanzas"; st.rerun()

        elif st.session_state.view == "Marcas":
            if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
            st.header("📋 Mis Registros")
            df = leer_hoja_cache(GID_MARCAS); df.columns = df.columns.str.strip()
            mi_id = str(int(float(user['ID_Biometrico'])))
            col_id = df.columns[0]; df[col_id] = df[col_id].astype(str).str.strip().str.replace('.0', '', regex=False)
            m = df[df[col_id] == mi_id].copy().drop_duplicates(subset=['Fecha', 'Hora', 'Evento'])
            if not m.empty:
                m['temp_f'] = pd.to_datetime(m['Fecha'], dayfirst=True)
                m['temp_h'] = pd.to_datetime(m['Hora'], format='%H:%M').dt.time
                h_i = date.today() - timedelta(days=7)
                r = st.date_input("Rango:", value=(h_i, date.today()), format="DD/MM/YYYY")
                m_f = m[(m['temp_f'].dt.date >= r[0]) & (m['temp_f'].dt.date <= r[1])].copy() if (isinstance(r, tuple) and len(r)==2) else m.copy()
                # Tardanzas mes actual
                mes_a = m[(m['temp_f'].dt.month == datetime.now().month) & (m['temp_f'].dt.year == datetime.now().year)]
                lim_i, lim_f = datetime.strptime("08:11", "%H:%M").time(), datetime.strptime("09:00", "%H:%M").time()
                tar = mes_a[(mes_a['temp_h'] >= lim_i) & (mes_a['temp_h'] <= lim_f) & (mes_a['Evento'].str.strip().isin(['Entrada', 'Acceso']))]
                if not tar.empty:
                    st.error(f"⚠️ Llegadas tarde en {datetime.now().strftime('%B')}: {len(tar)}")
                    st.write(f"Días: {', '.join(tar['Fecha'].tolist())}")
                st.dataframe(m_f.drop(columns=['temp_f', 'temp_h']), use_container_width=True, hide_index=True)
            else: st.info("Sin registros.")

        elif st.session_state.view == "Vacaciones":
            if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
            st.header("🏖️ Solicitar LAR")
            df_s = leer_hoja_cache(GID_SOLICITUDES); df_s.columns = df_s.columns.str.strip()
            dni_u = str(user['DNI']).split('.')[0]
            m_lar = df_s[(df_s['DNI'].astype(str) == dni_u) & (df_s['Tipo'] == 'LAR')]
            rem = float(user['Dias_Totales']) - m_lar['Dias_Habiles'].sum()
            st.metric("Días LAR Disponibles", f"{int(rem)}")
            if len(m_lar) < 2:
                f_i = st.date_input("Inicio", format="DD/MM/YYYY")
                f_f = st.date_input("Fin", min_value=f_i, format="DD/MM/YYYY")
                try:
                    df_f = leer_hoja_cache(GID_FERIADOS)
                    l_f = set(pd.to_datetime(df_f['Fecha'], dayfirst=True, errors='coerce').dropna().dt.date.tolist())
                except: l_f = set()
                d_p = len([f_i+timedelta(days=i) for i in range((f_f-f_i).days+1) if (f_i+timedelta(days=i)).weekday()<5 and (f_i+timedelta(days=i)) not in l_f])
                if d_p > 0:
                    st.info(f"Días: {d_p} | Nuevo saldo: {int(rem-d_p)}")
                    if rem >= d_p and st.checkbox("Confirmo fechas"):
                        if st.button("🚀 ENVIAR"):
                            p = {"dni": dni_u, "nombre": user['Nombre'], "inicio": f_i.strftime('%d/%m/%Y'), "fin": f_f.strftime('%d/%m/%Y'), "dias": d_p, "tipo": "LAR"}
                            if requests.post(URL_MACRO, json=p).status_code == 200:
                                st.success("✅ Solicitud Realizada")
                                h = datetime.now(); meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                                dias_s = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                                n_let = numero_a_letras(d_p)
                                nota = f"SOLICITUD DE LICENCIA\nSALTA, {dias_s[h.weekday()]} {h.day} de {meses[h.month-1]} de {h.year}\n\nPor la presente solicito LICENCIA ANUAL ORDINARIA/2025 del {f_i.strftime('%d/%m/%Y')} al {f_f.strftime('%d/%m/%Y')} inclusive, por el termino de {d_p} ({n_let}) días hábiles.\n\n\n..................          ..................\n V°B° del Jefe             Firma Solicitante"
                                st.text_area("Copia para imprimir:", nota, height=300)
                                enviar_correo("rrhhparqueautomotor@gmail.com", f"LAR: {user['Nombre']}", nota)
                                st.cache_data.clear()
            else: st.error("Límite de partes alcanzado.")

        elif st.session_state.view == "Art74":
            if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
            st.header("📄 Artículo 74")
            df_s = leer_hoja_cache(GID_SOLICITUDES)
            dni_u = str(user['DNI']).split('.')[0]
            u_art = len(df_s[(df_s['DNI'].astype(str) == dni_u) & (df_s['Tipo'] == 'Art74')])
            st.metric("Días Art. 74 Disponibles", f"{2 - u_art}")
            if u_art < 2:
                f_a = st.date_input("Fecha:", format="DD/MM/YYYY")
                if st.button("🚀 ENVIAR ART. 74"):
                    p = {"dni": dni_u, "nombre": user['Nombre'], "inicio": f_a.strftime('%d/%m/%Y'), "fin": f_a.strftime('%d/%m/%Y'), "dias": 1, "tipo": "Art74"}
                    if requests.post(URL_MACRO, json=p).status_code == 200:
                        st.success("✅ Solicitud Realizada")
                        enviar_correo("rrhhparqueautomotor@gmail.com", f"ART 74: {user['Nombre']}", f"Solicitud Art 74 para el {f_a}")
                        st.cache_data.clear()

        elif st.session_state.view == "Historial":
            if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
            st.header("🔍 Mis Solicitudes")
            df_s = leer_hoja_cache(GID_SOLICITUDES)
            dni_u = str(user['DNI']).split('.')[0]
            m_s = df_s[df_s['DNI'].astype(str) == dni_u].copy()
            if not m_s.empty:
                def f_st(v):
                    v = str(v).strip()
                    if v == "Aprobado": return "✅ Aprobado"
                    if v == "Pendiente": return "⏳ Pendiente"
                    return "❌ Rechazado" if v == "Rechazado" else v
                m_s['Estado'] = m_s['Estado'].apply(f_st)
                st.dataframe(m_s[['Tipo', 'Fecha_Inicio', 'Fecha_Fin', 'Dias_Habiles', 'Estado']], use_container_width=True, hide_index=True)

        elif st.session_state.view == "AdminTardanzas":
            if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
            st.header("🚨 Reporte Admin")
            tab_ac, tab_an = st.tabs(["Mes en Curso", "Mes Anterior"])
            df_a = leer_hoja_cache(GID_MARCAS); df_a.columns = df_a.columns.str.strip()
            df_a['tf'] = pd.to_datetime(df_a['Fecha'], dayfirst=True)
            df_a['th'] = pd.to_datetime(df_a['Hora'], format='%H:%M').dt.time
            h = datetime.now(); a = h.replace(day=1) - timedelta(days=1)
            li, lf = datetime.strptime("08:11", "%H:%M").time(), datetime.strptime("09:00", "%H:%M").time()
            def r_rep(m, an):
                t = df_a[(df_a['tf'].dt.month == m) & (df_a['tf'].dt.year == an) & (df_a['th'] >= li) & (df_a['th'] <= lf) & (df_a['Evento'].str.strip().isin(['Entrada', 'Acceso']))].copy()
                if not t.empty:
                    for ag in sorted(t['Nombre'].unique()):
                        df_ag = t[t['Nombre'] == ag].sort_values('tf', ascending=False)
                        st.markdown(f"### **{ag}**")
                        st.write(f"Tardanzas: {len(df_ag.drop_duplicates(subset=['Fecha']))}")
                        st.dataframe(df_ag[['Fecha', 'Hora', 'Evento']], use_container_width=True, hide_index=True)
                else: st.info("Sin registros.")
            with tab_ac: r_rep(h.month, h.year)
            with tab_an: r_rep(a.month, a.year)

        elif st.session_state.view == "Feriados":
            if st.button("⬅️ Volver"): st.session_state.view = "Home"; st.rerun()
            st.header("🗓️ Feriados"); st.dataframe(leer_hoja_cache(GID_FERIADOS), use_container_width=True, hide_index=True)
