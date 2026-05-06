# ============================================================
# CONSTANTES DE INTEGRACIÓN - MICROSERVICIO DE COMPRAS
# ============================================================
# Aquí se centralizan TODAS las URLs de los microservicios externos.
# Cuando el Inge les asigne una IP estática a cada equipo,
# solo debes cambiar el valor aquí y todo el sistema se actualiza.
# ============================================================

# --- URL BASE DE ESTE MICROSERVICIO (para que otros nos llamen) ---
MS_COMPRAS_BASE_URL = "http://localhost:8000/api/"

# --- MICROSERVICIOS EXTERNOS ---

# MS Gestión Financiera (.NET) - DESPLEGADO EN RENDER
# Endpoints que NOSOTROS llamamos para consultar presupuesto y registrar pagos
MS_FINANZAS_BASE_URL = "https://gestionfinanciera.onrender.com/api/"
MS_FINANZAS_VERIFICAR_PRESUPUESTO = MS_FINANZAS_BASE_URL + "facturas/verificar-presupuesto"
MS_FINANZAS_REGISTRAR_PAGO = MS_FINANZAS_BASE_URL + "pagos/registrar"
MS_FINANZAS_PRESUPUESTO_MENSUAL = MS_FINANZAS_BASE_URL + "presupuesto-mensual"

# MS Gestión Legal (.NET) - YA DESPLEGADO EN RAILWAY
# Endpoint real: POST /api/Solicituds
# Campos: Codigo, TipoSolicitud, Motivo, Descripcion, FechaSolicitud
MS_LEGAL_BASE_URL = "https://gestionlegal-production.up.railway.app/api/"
MS_LEGAL_SOLICITAR_TOKEN = MS_LEGAL_BASE_URL + "Solicituds"

# MS Gestión de Inventarios (.NET)
# Endpoints que ELLOS nos llaman (o nosotros consultamos para stock crítico)
MS_INVENTARIO_BASE_URL = "http://localhost:5003/api/"
MS_INVENTARIO_CONSULTAR_STOCK = MS_INVENTARIO_BASE_URL + "insumos/stock/"

# MS Logística Hospitalaria (.NET)
# Endpoint que ELLOS llaman para crearnos una Requisición
# Nosotros exponemos: POST /api/requisiciones/
MS_LOGISTICA_BASE_URL = "http://localhost:5004/api/"
