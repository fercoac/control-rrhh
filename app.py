import streamlit as st
import pandas as pd
from datetime import datetime, date
import smtplib
from email.mime.text import MIMEText

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="RRHH - Parque Automotor", layout="centered")

# IDs de tu Google Sheet (Ya configurados con tus datos)
SHEET_ID = "1JwTFaSjcYLDLG6knoxXBkjPTZb2L9CGEWVCwXdswjpI"
GID_EMPLEADOS = "1680284558"
GID_MARCAS = "598259224"
GID_SOLICITUDES = "0"

# Función para leer datos desde Google Sheets como CSV
def leer_hoja(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

# Función para enviar notificaciones por mail
def enviar_correo(destinatario, asunto, cuerpo):
    remitente = "rrhhparqueautomotor@gmail.com"
    # REEMPLAZA LAS XX POR TU CLAVE DE 16 LETRAS DE GOOGLE
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
        st.warning(f"Solicitud generada, pero no se pudo enviar el correo de aviso: {e}")

# --- SISTEMA DE LOGIN ---
if 'auth' not in st.session_state:
    st.title("🔐 Control de Ingresos")
    st.write("Ingresa con tu DNI y el PIN de 4 dígitos.")
    
    dni_input = st.text_input("DNI")
    pin_input = st.text_input("Clave de 4 dígitos (PIN)", type="password")
    
    if st.button("Ingresar"):
        try:
            df_emp = leer_hoja(GID_EMPLEADOS)
            # Limpieza de datos para asegurar coincidencia
            df_emp['DNI'] = df_emp['DNI'].astype(str).str.strip().str.replace('.0', '', regex=False)
            df_emp['PIN'] = df_emp['PIN'].astype(str).str.strip().str.replace('.0', '', regex=False).str.zfill(4)
            
            # Buscamos al usuario por DNI y PIN
            user_row = df_emp[(df_emp['DNI'] == str(dni_input).strip()) & (df_emp['PIN'] == str(pin_input).strip())]
            
            if not user_row.empty:
                st.session_state.auth = True
                st.session_state.user = user_row.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("DNI o Clave incorrectos. Revisa tu PIN en el archivo Excel.")
        except Exception as e:
            st.error(f"Error de conexión con la base de datos: {e}")

# --- PANEL DEL EMPLEADO LOGUEADO ---
else:
    user = st.session_state.user
    st.sidebar.title(f"Hola, {user['Nombre']}")
    opcion = st.sidebar.radio("Ir a:", ["Mis Marcas", "Solicitar Vacaciones"])

    # SECCIÓN DE MARCAS
    if opcion == "Mis Marcas":
        st.header("📋 Mis Registros")
        try:
            df_marcas = leer_hoja(GID_MARCAS)
            # Limpiamos el ID del usuario y de la tabla para comparar correctamente
            mi_id = str(int(float(user['ID_Biometrico'])))
            df_marcas['ID'] = df_marcas['ID'].astype(str).str.strip().str.replace('.0', '', regex=False)
            
            # Filtramos marcas del empleado
            mis_marcas = df_marcas[df_marcas['ID'] == mi_id]
            
            if not mis_marcas.empty:
                st.write(f"Mostrando registros para el ID: {mi_id}")
                st.dataframe(mis_marcas[['Fecha', 'Hora', 'Evento']], use_container_width=True)
            else:
                st.info(f"No se encontraron registros de ingreso/salida para el ID {mi_id}")
        except Exception as e:
            st.info("No se pudieron cargar las marcas. Asegúrate de que el archivo del reloj esté pegado en la pestaña 'Marcas'.")

    # SECCIÓN DE VACACIONES
    elif opcion == "Solicitar Vacaciones":
        st.header("🏖️ Solicitud de Licencia (L.A.R.)")
        try:
            df_sol = leer_hoja(GID_SOLICITUDES)
            df_sol['DNI'] = df_sol['DNI'].astype(str).str.strip()
            mis_sol = df_sol[df_sol['DNI'] == str(user['DNI'])]
            dias_usados = mis_sol['Dias_Habiles'].sum()
        except:
            dias_usados = 0
            mis_sol = pd.DataFrame()

        remanente = float(user['Dias_Totales']) - dias_usados
        partes_pedidas = len(mis_sol)

        col1, col2 = st.columns(2)
        col1.metric("Días Disponibles", f"{int(remanente)}")
        col2.metric("Partes Utilizadas", f"{partes_pedidas} / 2")

        if partes_pedidas < 2 and remanente > 0:
            with st.form("form_vac"):
                f_inicio = st.date_input("Fecha de Inicio", min_value=date(2025, 12, 1), max_value=date(2026, 11, 30))
                f_fin = st.date_input("Fecha de Fin", min_value=f_inicio, max_value=date(2026, 11, 30))
                
                if st.form_submit_button("Generar Solicitud Formal"):
                    # Cálculo de días hábiles (Lunes a Viernes)
                    rango = pd.bdate_range(start=f_inicio, end=f_fin)
                    dias_pedidos = len(rango)

                    if dias_pedidos <= remanente:
                        # Nota Formal para imprimir
                        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
                        nota_texto = f"""
SALTA, {fecha_hoy}

Sr. Subsecretario del Parque Automotor
Ricardo Velarde Figueroa
S__________/__________D

Tengo el agrado de dirigirme a Usted, a fin de solicitar autorización para hacer uso de mi Licencia Anual Reglamentaria — L.A.R., correspondiente al período 2025-2026, por la cantidad de {dias_pedidos} días hábiles, a partir del día {f_inicio.strftime('%d/%m/%Y')} y hasta el día {f_fin.strftime('%d/%m/%Y')}, inclusive.

La presente solicitud se efectúa quedando sujeta a la autorización correspondiente y a las necesidades de servicio del área.

Sin otro particular, saludo a Usted atentamente.

Firma: _______________________________
Apellido y Nombre: {user['Nombre']}
D.N.I.: {user['DNI']}
Teléfono de contacto: {user['Telefono']}
                        """
                        st.success("✅ Solicitud generada con éxito.")
                        st.text_area("Copia el siguiente texto para imprimir y firmar:", nota_texto, height=400)
                        
                        # Notificación al administrador
                        enviar_correo("rrhhparqueautomotor@gmail.com", 
                                      f"Nueva LAR: {user['Nombre']}", 
                                      f"El empleado {user['Nombre']} ha solicitado {dias_pedidos} días hábiles de LAR.")
                    else:
                        st.error(f"No tienes días suficientes. Solicitaste {dias_pedidos} y te quedan {int(remanente)}.")
        else:
            st.warning("Has alcanzado el límite de partes o no tienes días disponibles para este periodo.")

    if st.sidebar.button("Cerrar Sesión"):
        del st.session_state.auth
        st.rerun()
