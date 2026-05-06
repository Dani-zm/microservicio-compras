import os
import django
from decimal import Decimal

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from compras.models import (
    Proveedor, Producto, ProveedorProducto, RequisicionInterna, 
    OrdenCompra, DetalleOrden, RecepcionPedido, PresupuestoMensual
)

def poblar_base_de_datos():
    print("Iniciando carga de datos de prueba...")

    # 1. Crear Presupuestos Mensuales
    print("Creando Presupuestos Mensuales...")
    p1, _ = PresupuestoMensual.objects.get_or_create(
        periodo="2026-05",
        defaults={
            "monto_asignado": Decimal("50000.00"),
            "monto_disponible": Decimal("50000.00"),
            "observaciones": "Presupuesto inicial asignado por Finanzas para mayo"
        }
    )
    
    p2, _ = PresupuestoMensual.objects.get_or_create(
        periodo="2026-04",
        defaults={
            "monto_asignado": Decimal("40000.00"),
            "monto_disponible": Decimal("5000.00"), # Simular presupuesto casi agotado
            "observaciones": "Presupuesto del mes pasado"
        }
    )

    # 2. Crear Proveedores
    print("Creando Proveedores...")
    prov1, _ = Proveedor.objects.get_or_create(
        codigo_proveedor="PROV-001",
        defaults={"nombre_proveedor": "Pharma Corp", "nit_proveedor": "12345678", "estado": "Activo"}
    )
    prov2, _ = Proveedor.objects.get_or_create(
        codigo_proveedor="PROV-002",
        defaults={"nombre_proveedor": "Insumos Hospitalarios S.A.", "nit_proveedor": "87654321", "estado": "Activo"}
    )

    # 3. Crear Productos
    print("Creando Productos...")
    prod1, _ = Producto.objects.get_or_create(
        codigo_producto="PROD-001",
        defaults={"nombre_producto": "Fentanilo Ampolla", "unidad_medida": "Ampolla", "es_controlado": True}
    )
    prod2, _ = Producto.objects.get_or_create(
        codigo_producto="PROD-002",
        defaults={"nombre_producto": "Paracetamol 500mg", "unidad_medida": "Caja", "es_controlado": False}
    )
    prod3, _ = Producto.objects.get_or_create(
        codigo_producto="PROD-003",
        defaults={"nombre_producto": "Jeringas 5ml", "unidad_medida": "Unidad", "es_controlado": False}
    )

    # 4. Crear Relación Proveedor_Producto
    print("Creando Catálogo Proveedor-Producto...")
    ProveedorProducto.objects.get_or_create(
        codigo_proveedor_producto="CAT-001",
        defaults={"id_proveedor": prov1, "id_producto": prod1, "precio_referencial": Decimal("300.00")}
    )
    ProveedorProducto.objects.get_or_create(
        codigo_proveedor_producto="CAT-002",
        defaults={"id_proveedor": prov1, "id_producto": prod2, "precio_referencial": Decimal("50.00")}
    )
    ProveedorProducto.objects.get_or_create(
        codigo_proveedor_producto="CAT-003",
        defaults={"id_proveedor": prov2, "id_producto": prod3, "precio_referencial": Decimal("2.50")}
    )

    # 5. Crear Requisiciones
    print("Creando Requisiciones Internas...")
    req1, _ = RequisicionInterna.objects.get_or_create(
        codigo_requisicion="REQ-2026-001",
        defaults={"area_solicitante": "Quirófano", "origen": "Cirugía", "urgencia": "Alta"}
    )
    req2, _ = RequisicionInterna.objects.get_or_create(
        codigo_requisicion="REQ-2026-002",
        defaults={"area_solicitante": "Pediatría", "origen": "Consulta Externa", "urgencia": "Media"}
    )

    # 6. Crear Órdenes de Compra
    print("Creando Órdenes de Compra...")
    ord1, _ = OrdenCompra.objects.get_or_create(
        codigo_orden="ORD-2026-001",
        defaults={
            "id_proveedor": prov1, 
            "id_requisicion": req1, 
            "monto_total": Decimal("15000.00"),
            "estado": "Emitida"
        }
    )
    ord2, _ = OrdenCompra.objects.get_or_create(
        codigo_orden="ORD-2026-002",
        defaults={
            "id_proveedor": prov2, 
            "id_requisicion": req2, 
            "monto_total": Decimal("500.00"),
            "estado": "Pendiente",
            "presupuesto_asignado": Decimal("50000.00"),
            "id_validacion_financiera": "FIN-VAL-999" # Validada por finanzas
        }
    )

    # 7. Crear Detalles de Orden
    print("Creando Detalles de Orden...")
    DetalleOrden.objects.get_or_create(
        codigo_detalle="DET-001",
        defaults={"id_orden": ord1, "id_producto": prod1, "cantidad": 50, "precio": Decimal("300.00")}
    )
    DetalleOrden.objects.get_or_create(
        codigo_detalle="DET-002",
        defaults={"id_orden": ord2, "id_producto": prod3, "cantidad": 200, "precio": Decimal("2.50")}
    )

    # 8. Crear Recepciones de Pedidos
    print("Creando Recepciones de Pedido...")
    RecepcionPedido.objects.get_or_create(
        codigo_recepcion="REC-2026-001",
        defaults={
            "id_orden": ord1, 
            "factura_numero": None,  # Para probar Consulta Genérica 6 (Sin factura)
            "recibido_conforme": True,
            "observaciones_recepcion": "Entrega parcial"
        }
    )
    RecepcionPedido.objects.get_or_create(
        codigo_recepcion="REC-2026-002",
        defaults={
            "id_orden": ord2, 
            "factura_numero": "FAC-100234",
            "recibido_conforme": False, # Para probar Consulta Genérica 7 (Inconformes)
            "observaciones_recepcion": "Cajas maltratadas"
        }
    )

    print("¡Base de datos poblada exitosamente con todos los modelos!")

if __name__ == '__main__':
    poblar_base_de_datos()
