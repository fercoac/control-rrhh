import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
import requests

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# Datos de conexión
URL_MACRO = "https://script.google.com/macros/s/AKfycby42PKm1KqL0IaqAKfumxB_9_856yueCpJOWx1ersgmb218g6R3sU0Y0SKRQ-ZIQ4Fj/exec"
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"
GID_MARCAS = "598259224"
GID_SOLICITUDES = "0"
GID_FERIADOS = "320254015" 

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
    except:
        return False

# --- LOGIN ---
if 'auth' not in st.session_state:
    st.title("🔐 Control de Ingresos")
    dni_input = st.text_input("DNI")
    pin_input = st.text_input("Clave de 4 dígitos", type="password")
    
    if st.button("Ingresar"):
        try:
            url_emp = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_EMPLEADOS}"
            df_emp = pd.read_csv(url_emp)
            df_emp.columns = df_emp.columns.str.strip()
            df_emp['DNI'] = df_emp['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
            df_emp['PIN'] = df_emp['PIN'].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(4)
            user_row = df_emp[(df_emp['DNI'] == str(dni_input).strip()) & (df_emp['PIN'] == str(pin_input).strip())]
            
            if not user_row.empty:
                st.session_state.auth = True
                st.session_state.user = user_row.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("DNI o Clave incorrectos.")
        except:
            st.error("Error de conexión con la base de datos.")

# --- PANEL PRINCIPAL ---
else:
    user = st.session_state.user
    st.sidebar.title(f"Hola, {user['Nombre']}")
    opcion = st.sidebar.radio("Menú:", ["Mis Marcas", "Solicitar Vacaciones"])

    if opcion == "Mis Marcas":
        st.header("📋 Mis Registros")
        try:
            url_marcas = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_MARCAS}"
            df_marcas = pd.read_csv(url_marcas)
            df_marcas.columns = df_marcas.columns.str.strip()
            mi_id = str(int(float(user['ID_Biometrico'])))
            col_id = df_marcas.columns[0]
            df_marcas[col_id] = df_marcas[col_id].astype(str).str.strip().str.replace('.0', '', regex=False)
            mis_marcas = df_marcas[df_marcas[col_id] == mi_id]
            st.dataframe(mis_marcas, use_container_width=True, hide_index=True)
        except:
            st.error("Error al cargar registros.")

    elif opcion == "Solicitar Vacaciones":
        st.header("🏖️ Solicitud de Licencia (L.A.R.)")
        
        # Cargar Feriados
        try:
            url_feriados = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_FERIADOS}"
            df_feriados = pd.read_csv(url_feriados)
            df_feriados.columns = df_feriados.columns.str.strip()
            fechas_sucias = pd.to_datetime(df_feriados['Fecha'], dayfirst=True, errors='coerce')
            lista_feriados = set(fechas_sucias.dropna().dt.date.tolist())
        except:
            lista_feriados = set()

        # Cargar Solicitudes para calcular remanente
        try:
            url_sol = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_SOLICITUDES}"
            df_sol = pd.read_csv(url_sol)
            df_sol.columns = df_sol.columns.str.strip()
            df_sol['DNI'] = df_sol['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
            mis_sol = df_sol[df_sol['DNI'] == str(user['DNI']).split('.')[0]]
            dias_usados = mis_sol['Dias_Habiles'].sum()
        except:
            dias_usados = 0

        remanente_actual = float(user['Dias_Totales']) - dias_usados
        st.metric("Días Disponibles Hoy", f"{int(remanente_actual)}")

        f_inicio = st.date_input("Fecha Inicio", min_value=date(2025, 12, 1), format="DD/MM/YYYY")
        f_fin = st.date_input("Fecha Fin", min_value=f_inicio, format="DD/MM/YYYY")
        
        # Cálculo de días
        cantidad_dias_total = (f_fin - f_inicio).days + 1
        dias_habiles_lista = [f_inicio + timedelta(days=i) for i in range(cantidad_dias_total) if (f_inicio + timedelta(days=i)).weekday() < 5 and (f_inicio + timedelta(days=i)) not in lista_feriados]
        dias_pedidos = len(dias_habiles_lista)
        nuevo_remanente = remanente_actual - dias_pedidos

        if dias_pedidos > 0:
            st.info(f"🧾 Días a solicitar: **{dias_pedidos}** | Saldo restante: **{int(nuevo_remanente)}**")
            
            if nuevo_remanente >= 0:
                confirmar = st.checkbox("Confirmo que las fechas son correctas.")
                if confirmar:
                    if st.button("🚀 ENVIAR SOLICITUD Y GUARDAR"):
                        # 1. ENVIAR DATOS AL EXCEL
                        dni_limpio = str(user['DNI']).split('.')[0]
                        payload = {
                            "dni": dni_limpio,
                            "nombre": user['Nombre'],
                            "inicio": f_inicio.strftime('%d/%m/%Y'),
                            "fin": f_fin.strftime('%d/%m/%Y'),
                            "dias": dias_pedidos
                        }
                        
                        with st.spinner('Guardando en base de datos...'):
                            try:
                                response = requests.post(URL_MACRO, json=payload)
                                if response.status_code == 200:
                                    st.success("✅ ¡Registrado en el Excel con éxito!")
                                    
                                    # 2. GENERAR NOTA Y MAIL
                                    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                                    hoy = datetime.now()
                                    fecha_salta = f"SALTA, {hoy.day} de {meses[hoy.month-1]} de {hoy.year}"
                                    texto_dias = "día" if dias_pedidos == 1 else "días"
                                    
                                    nota = f"{fecha_salta}\n\nSr. Subsecretario del Parque Automotor\nRicardo Velarde Figueroa\nS__________/__________D\n\nTengo el agrado de dirigirme a Usted, a fin de solicitar autorización para hacer uso de mi Licencia Anual Reglamentaria — L.A.R., correspondiente al período 2025-2026, por la cantidad de {dias_pedidos} {texto_dias} hábiles, a partir del día {f_inicio.strftime('%d/%m/%Y')} y hasta el día {f_fin.strftime('%d/%m/%Y')}, inclusive.\n\nFirma: _______________________________\nApellido y Nombre: {user['Nombre']}\nD.N.I.: {dni_limpio}"
                                    
                                    st.text_area("Copia para imprimir:", nota, height=400)
                                    enviar_correo("rrhhparqueautomotor@gmail.com", f"SOLICITUD LAR: {user['Nombre']}", nota)
                                else:
                                    st.error("Error al guardar: El servidor de Google no respondió correctamente.")
                            except Exception as e:
                                st.error(f"Error de conexión al guardar: {e}")

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth
        st.rerun()
