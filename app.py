import streamlit as st
import pandas as pd
from datetime import datetime, date
import smtplib
from email.mime.text import MIMEText

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# Datos de conexión (Tus GIDs confirmados)
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"
GID_MARCAS = "598259224"
GID_SOLICITUDES = "0"

# Función para enviar correo
def enviar_correo(destinatario, asunto, cuerpo):
    remitente = "rrhhparqueautomotor@gmail.com"
    password = "uwqiaqcuovcjejuk" 
    msg = MIMEText(cuerpo)
    msg['Subject'] = asunto
    msg['From'] = remitente
    msg['To'] = destinatario
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(remitente, password)
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
    except Exception as e:
        st.warning(f"Error al enviar el mail: {e}")

# --- LOGIN ---
if 'auth' not in st.session_state:
    st.title("🔐 Control de Ingresos")
    dni_input = st.text_input("DNI")
    pin_input = st.text_input("Clave de 4 dígitos", type="password")
    
    if st.button("Ingresar"):
        try:
            url_emp = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_EMPLEADOS}"
            df_emp = pd.read_csv(url_emp)
            # Limpieza de títulos de columnas
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
        except Exception as e:
            st.error(f"Error de conexión: {e}")

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
            
            # --- LIMPIEZA DE COLUMNAS (Para evitar el error 'Fecha' not in index) ---
            df_marcas.columns = df_marcas.columns.str.strip()
            
            # Limpiamos IDs para comparar
            mi_id = str(int(float(user['ID_Biometrico'])))
            # Buscamos la columna de ID (generalmente es la primera)
            col_id = df_marcas.columns[0] 
            df_marcas[col_id] = df_marcas[col_id].astype(str).str.strip().str.replace('.0', '', regex=False)
            
            mis_marcas = df_marcas[df_marcas[col_id] == mi_id]
            
            if not mis_marcas.empty:
                st.write(f"Mostrando marcas para el ID: {mi_id}")
                # Mostramos todas las columnas que existan para no fallar
                st.dataframe(mis_marcas, use_container_width=True)
            else:
                st.info(f"No hay registros para el ID {mi_id}")
        except Exception as e:
            st.error(f"Error al cargar marcas: {e}")

    elif opcion == "Solicitar Vacaciones":
        st.header("🏖️ Solicitud de Licencia (L.A.R.)")
        try:
            url_sol = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_SOLICITUDES}"
            df_sol = pd.read_csv(url_sol)
            df_sol.columns = df_sol.columns.str.strip()
            df_sol['DNI'] = df_sol['DNI'].astype(str).str.strip()
            mis_sol = df_sol[df_sol['DNI'] == str(user['DNI'])]
            dias_usados = mis_sol['Dias_Habiles'].sum()
        except:
            dias_usados = 0

        remanente = float(user['Dias_Totales']) - dias_usados
        st.metric("Días Disponibles", f"{int(remanente)}")

        with st.form("form_v"):
            f_inicio = st.date_input("Fecha Inicio", min_value=date(2025, 12, 1))
            f_fin = st.date_input("Fecha Fin", min_value=f_inicio)
            
            if st.form_submit_button("Generar Solicitud"):
                dias = len(pd.bdate_range(f_inicio, f_fin))
                if dias <= remanente:
                    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                    hoy = datetime.now()
                    fecha_salta = f"SALTA, {hoy.day} de {meses[hoy.month-1]} de {hoy.year}"

                    nota = f"""
{fecha_salta}

Sr. Subsecretario del Parque Automotor
Ricardo Velarde Figueroa
S__________/__________D

Tengo el agrado de dirigirme a Usted, a fin de solicitar autorización para hacer uso de mi Licencia Anual Reglamentaria — L.A.R., correspondiente al período 2025-2026, por la cantidad de {dias} días hábiles, a partir del día {f_inicio.strftime('%d/%m/%Y')} y hasta el día {f_fin.strftime('%d/%m/%Y')}, inclusive.

Firma: _______________________________
Apellido y Nombre: {user['Nombre']}
D.N.I.: {user['DNI']}
Teléfono: {user['Telefono']}
                    """
                    st.success("✅ Solicitud lista.")
                    st.text_area("Copie este texto:", nota, height=350)
                    enviar_correo("rrhhparqueautomotor@gmail.com", f"SOLICITUD LAR: {user['Nombre']}", nota)
                else:
                    st.error(f"Días insuficientes (le quedan {int(remanente)}).")

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth
        st.rerun()
