from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Exists, OuterRef, F
from django.utils import timezone
import requests as http_requests

from .models import (
    Proveedor, Producto, ProveedorProducto, RequisicionInterna, 
    OrdenCompra, DetalleOrden, RecepcionPedido, PresupuestoMensual
)
from .serializers import (
    ProveedorSerializer, ProductoSerializer, ProveedorProductoSerializer,
    RequisicionInternaSerializer, OrdenCompraSerializer, DetalleOrdenSerializer,
    RecepcionPedidoSerializer, PresupuestoMensualSerializer
)
from .constants import MS_LEGAL_SOLICITAR_TOKEN

class SoftDeleteModelViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # Regla 4: Todas las consultas deben considerar únicamente registros activos.
        # En compras tenemos estados válidos como 'Pendiente' o 'Emitida'. 
        # Por tanto, el Soft Delete excluye a los 'Inactivos' en lugar de forzar a 'Activo'.
        return self.queryset.exclude(estado='Inactivo')

    def perform_destroy(self, instance):
        instance.estado = 'Inactivo'
        instance.save()

#https://urianviera.com/django/domina-las-queries-en-django-desde-cero

class ProveedorViewSet(SoftDeleteModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    lookup_field = 'codigo_proveedor' 


class ProductoViewSet(SoftDeleteModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    lookup_field = 'codigo_producto'


class ProveedorProductoViewSet(SoftDeleteModelViewSet):
    queryset = ProveedorProducto.objects.all()
    serializer_class = ProveedorProductoSerializer
    lookup_field = 'codigo_proveedor_producto'


    @action(detail=False, methods=['get'])
    def join_dos_tablas(self, request):
        
        query = self.get_queryset().select_related('id_proveedor')
        
        datos_respuesta = []
        for relacion in query:
            if relacion.id_proveedor.estado == 'Activo':
                datos_respuesta.append({
                    'codigo_relacion': relacion.codigo_proveedor_producto,
                    'nombre_proveedor': relacion.id_proveedor.nombre_proveedor,
                    'nit_proveedor': relacion.id_proveedor.nit_proveedor,
                    'precio_referencial': relacion.precio_referencial
                })
        
        return Response(datos_respuesta, status=status.HTTP_200_OK)


    @action(detail=False, methods=['get'])
    def join_tres_tablas(self, request):
        query = self.get_queryset().select_related('id_proveedor', 'id_producto')
        
        datos_respuesta = []
        for rel in query:
            if rel.id_proveedor.estado == 'Activo' and rel.id_producto.estado == 'Activo':
                datos_respuesta.append({
                    'proveedor_nombre': rel.id_proveedor.nombre_proveedor,
                    'producto_nombre': rel.id_producto.nombre_producto,
                    'producto_descripcion': rel.id_producto.descripcion,
                    'unidad_medida': rel.id_producto.unidad_medida,
                    'precio_ofrecido': rel.precio_referencial,
                    'fecha_actualizacion': rel.fecha_actualizacion_precio
                })
                
        return Response(datos_respuesta, status=status.HTTP_200_OK)


# --- CONTROLADORES "Tarea 4" ---

class RequisicionInternaViewSet(SoftDeleteModelViewSet):
    queryset = RequisicionInterna.objects.all()
    serializer_class = RequisicionInternaSerializer
    lookup_field = 'codigo_requisicion'

    # Consulta Genérica 5: Requisiciones sin Órdenes generadas
    @action(detail=False, methods=['get'])
    def requisiciones_sin_ordenes(self, request):
        subquery = OrdenCompra.objects.exclude(estado='Inactivo').filter(id_requisicion=OuterRef('pk'))
        query = self.get_queryset().annotate(tiene_orden=Exists(subquery)).filter(tiene_orden=False)
        
        datos = [{'codigo': req.codigo_requisicion, 'area': req.area_solicitante, 'urgencia': req.urgencia} for req in query]
        return Response(datos, status=status.HTTP_200_OK)

    # CU-04 (Jefe Compras): Cantidad de órdenes de compra generadas por área solicitante 
    @action(detail=False, methods=['get'])
    def ordenes_por_area(self, request):
        query = self.get_queryset().annotate(total_ordenes=Count('ordenes_generadas')).values('area_solicitante', 'total_ordenes')
        return Response(list(query), status=status.HTTP_200_OK)

    # ENDPOINT FAKE PARA LOGÍSTICA (Integración Universidad)
    @action(detail=False, methods=['post'], url_path='recibir_pedido_logistica')
    def recibir_pedido_logistica(self, request):
        # Simulamos que recibimos la petición de logística
        data = request.data
        return Response({
            "mensaje": "Pedido de logística recibido correctamente. Procesando requisición de insumos.",
            "datos_recibidos": data,
            "estado": "En revisión"
        }, status=status.HTTP_201_CREATED)

    # ENDPOINT FAKE PARA MANTENIMIENTO Y ACTIVOS (Integración Universidad)
    @action(detail=False, methods=['post'], url_path='recibir_solicitud_activo')
    def recibir_solicitud_activo(self, request):
        data = request.data
        return Response({
            "mensaje": "Solicitud de activo/repuesto de Mantenimiento recibida correctamente.",
            "datos_recibidos": data,
            "estado": "Pendiente de Presupuesto"
        }, status=status.HTTP_201_CREATED)


class OrdenCompraViewSet(SoftDeleteModelViewSet):
    queryset = OrdenCompra.objects.all()
    serializer_class = OrdenCompraSerializer
    lookup_field = 'codigo_orden'
    lookup_value_regex = '[^/]+'  # Permite puntos (.) en el código de orden (como los autogenerados con milisegundos)
    
    def list(self, request, *args, **kwargs):
        # Sincronización automática con Gestión Legal al cargar la tabla
        ordenes_pendientes = self.get_queryset().filter(token_legal="Enviado a Legal")
        
        if ordenes_pendientes.exists():
            try:
                # Consultamos la lista completa de revisiones de Legal
                respuesta_revisiones = http_requests.get(
                    "https://gestionlegal-production.up.railway.app/api/SolicitudRevisions/listaCompleta",
                    timeout=5
                )
                if respuesta_revisiones.status_code == 200:
                    revisiones = respuesta_revisiones.json()
                    
                    # Para cada orden pendiente, buscamos si hay una revisión
                    for orden in ordenes_pendientes:
                        revision = next((r for r in revisiones if r.get('codigoSolicitud') == orden.codigo_orden), None)
                        if revision:
                            resultado = revision.get('resultado')
                            obs = revision.get('observaciones', '')
                            codigo_rev = revision.get('codigo', 'Aprobado')
                            
                            if resultado == 'Aprobado':
                                orden.token_legal = codigo_rev
                                orden.observaciones = f"Aprobado por Legal: {obs}"
                            else:
                                orden.token_legal = "Rechazado"
                                orden.observaciones = f"Rechazado por Legal: {obs}"
                                
                            orden.save(update_fields=['token_legal', 'observaciones'])
            except Exception:
                pass # Si la API de Legal está caída, ignoramos el error para no romper nuestra tabla

        return super().list(request, *args, **kwargs)

    # Consulta Genérica 2:(Órdenes por Requisición)
    @action(detail=False, methods=['get'])
    def cantidad_por_requisicion(self, request):
        query = self.get_queryset().values('id_requisicion__codigo_requisicion').annotate(total=Count('id_orden'))
        datos = [{'codigo_requisicion': item['id_requisicion__codigo_requisicion'], 'total_ordenes': item['total']} for item in query if item['id_requisicion__codigo_requisicion']]
        return Response(datos, status=status.HTTP_200_OK)

    # Consulta Genérica 3: (Gasto por Proveedor)
    @action(detail=False, methods=['get'])
    def gasto_por_proveedor(self, request):
        query = self.get_queryset().values('id_proveedor__nombre_proveedor').annotate(gasto_total=Sum('monto_total')).order_by('-gasto_total')
        datos = [{'proveedor': item['id_proveedor__nombre_proveedor'], 'gasto_total': item['gasto_total']} for item in query]
        return Response(datos, status=status.HTTP_200_OK)

    # CU-01 (Jefe Compras): Monto total de órdenes agrupadas por urgencia 
    @action(detail=False, methods=['get'])
    def monto_total_por_urgencia(self, request):
        query = self.get_queryset().values('id_requisicion__urgencia').annotate(total=Sum('monto_total'))
        datos = [{'urgencia': item['id_requisicion__urgencia'], 'monto_total': item['total']} for item in query if item['id_requisicion__urgencia']]
        return Response(datos, status=status.HTTP_200_OK)

    # CU-03 (Jefe Compras): Consultar órdenes atrasadas 
    @action(detail=False, methods=['get'])
    def ordenes_atrasadas(self, request):
        query = self.get_queryset().filter(fecha_estimada_entrega__lt=timezone.now())
        datos = [{'codigo': ord.codigo_orden, 'fecha_estimada': ord.fecha_estimada_entrega, 'monto': ord.monto_total} for ord in query]
        return Response(datos, status=status.HTTP_200_OK)

    # CU-05 (Administrador): Órdenes que superan los 10000 Bs presupuestados
    @action(detail=False, methods=['get'])
    def ordenes_alto_presupuesto(self, request):
        query = self.get_queryset().filter(presupuesto_asignado__gt=10000)
        datos = [{'codigo': ord.codigo_orden, 'presupuesto': ord.presupuesto_asignado, 'validacion': ord.id_validacion_financiera} for ord in query]
        return Response(datos, status=status.HTTP_200_OK)

    # CU-07 (Administrador): Órdenes que no cuentan con validación financiera
    @action(detail=False, methods=['get'])
    def sin_validacion_financiera(self, request):
        query = self.get_queryset().filter(id_validacion_financiera__isnull=True)
        datos = [{'codigo': ord.codigo_orden, 'monto': ord.monto_total, 'observaciones': ord.observaciones} for ord in query]
        return Response(datos, status=status.HTTP_200_OK)

    # CU-08 (Administrador): Historial de montos totales validados 
    @action(detail=False, methods=['get'])
    def historial_validadas(self, request):
        query = self.get_queryset().filter(id_validacion_financiera__isnull=False)
        datos = [{'codigo': ord.codigo_orden, 'validacion': ord.id_validacion_financiera, 'monto': ord.monto_total} for ord in query]
        return Response(datos, status=status.HTTP_200_OK)

    # INTEGRACIÓN CON GESTIÓN LEGAL
    # Llama a la API de Legal para pedir token de un fármaco controlado
    # No necesita ningún dato en el body - solo el código de la orden en la URL
    @action(detail=True, methods=['post'], url_path='solicitar_legal')
    def solicitar_aprobacion_legal(self, request, *args, **kwargs):
        orden = self.get_object()

        # Busca productos controlados en los detalles de esta orden
        detalles_controlados = orden.detalles.filter(
            id_producto__es_controlado=True,
            estado__in=['Activo', 'Pendiente']
        ).select_related('id_producto')

        if not detalles_controlados.exists():
            return Response(
                {'mensaje': 'Esta orden no tiene productos controlados. No se necesita aprobación legal.'},
                status=status.HTTP_200_OK
            )

        # Si ya fue enviado, verificamos su estado en la lista de revisiones de Legal
        if orden.token_legal == "Enviado a Legal":
            try:
                # Consultamos la lista completa de revisiones
                respuesta_revisiones = http_requests.get(
                    "https://gestionlegal-production.up.railway.app/api/SolicitudRevisions/listaCompleta",
                    timeout=10
                )
                if respuesta_revisiones.status_code == 200:
                    revisiones = respuesta_revisiones.json()
                    # Buscamos si nuestra orden ya fue revisada
                    revision = next((r for r in revisiones if r.get('codigoSolicitud') == orden.codigo_orden), None)
                    
                    if revision:
                        resultado = revision.get('resultado')
                        obs = revision.get('observaciones', '')
                        codigo_rev = revision.get('codigo', 'Aprobado')
                        
                        if resultado == 'Aprobado':
                            orden.token_legal = codigo_rev
                            orden.observaciones = f"Aprobado por Legal: {obs}"
                        else:
                            orden.token_legal = "Rechazado"
                            orden.observaciones = f"Rechazado por Legal: {obs}"
                            
                        orden.save(update_fields=['token_legal', 'observaciones'])
                        return Response({
                            'mensaje': f"El estado ha sido actualizado a: {resultado}",
                            'token_legal': orden.token_legal
                        }, status=status.HTTP_200_OK)
                    else:
                        return Response({
                            'mensaje': 'La solicitud sigue en revisión por el equipo Legal. Aún no hay respuesta.'
                        }, status=status.HTTP_200_OK)
            except Exception as e:
                pass # Si falla, continúa e intenta enviar de nuevo (aunque dará error de código duplicado)

        # Si no ha sido enviado, toma el primer producto controlado para la solicitud
        detalle = detalles_controlados.first()
        nombre_producto = detalle.id_producto.nombre_producto

        payload = {
            "Codigo": orden.codigo_orden,
            "TipoSolicitud": "Narcotico",
            "Motivo": "Compra de fármaco controlado - Proceso hospitalario",
            "Descripcion": f"Producto: {nombre_producto} | Cantidad: {detalle.cantidad} | Orden: {orden.codigo_orden}",
            "FechaSolicitud": timezone.now().isoformat()
        }

        try:
            respuesta = http_requests.post(
                MS_LEGAL_SOLICITAR_TOKEN,
                params=payload,   # Legal exige query params según Swagger
                timeout=10
            )

            if respuesta.status_code in [200, 201]:
                texto_respuesta = respuesta.text.strip()
                
                # Legal responde con un texto plano "Solicitud creada correctamente."
                # Guardamos ese texto como confirmación temporal
                orden.token_legal = "Enviado a Legal"
                orden.observaciones = texto_respuesta
                orden.save(update_fields=['token_legal', 'observaciones'])

                return Response({
                    'mensaje': f'Solicitud enviada a Legal para {nombre_producto}.',
                    'token_legal': orden.token_legal,
                    'respuesta_legal': texto_respuesta
                }, status=status.HTTP_200_OK)
            else:
                orden.observaciones = f'Rechazado por Legal. Código: {respuesta.status_code}'
                orden.save(update_fields=['observaciones'])
                return Response({
                    'error': 'Gestión Legal rechazó la solicitud',
                    'detalle': respuesta.text
                }, status=status.HTTP_400_BAD_REQUEST)

        except http_requests.exceptions.ConnectionError:
            return Response(
                {'error': 'No se pudo conectar con Gestión Legal. Verifica que su servidor esté activo.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except http_requests.exceptions.Timeout:
            return Response(
                {'error': 'Tiempo de espera agotado al contactar Gestión Legal.'},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )


class DetalleOrdenViewSet(SoftDeleteModelViewSet):
    queryset = DetalleOrden.objects.all()
    serializer_class = DetalleOrdenSerializer
    lookup_field = 'codigo_detalle'

    # Consulta Genérica 1: (Detalles de Órdenes y Productos)
    @action(detail=False, methods=['get'])
    def catalogo_detalles(self, request):
        query = self.get_queryset().select_related('id_producto')
        datos = [{'codigo_detalle': det.codigo_detalle, 'producto': det.id_producto.nombre_producto, 'cantidad': det.cantidad, 'subtotal': det.subtotal} for det in query]
        return Response(datos, status=status.HTTP_200_OK)

    # CU-02 (Jefe Compras): Detalles de órdenes urgentes 
    @action(detail=False, methods=['get'])
    def detalles_urgentes(self, request):
        query = self.get_queryset().filter(id_orden__id_requisicion__urgencia='Alta').select_related('id_orden', 'id_producto')
        datos = [{'orden': det.id_orden.codigo_orden, 'producto': det.id_producto.nombre_producto, 'cantidad': det.cantidad} for det in query]
        return Response(datos, status=status.HTTP_200_OK)

    # CU-06 (Administrador): Suma de dinero gastado por cada producto
    @action(detail=False, methods=['get'])
    def gasto_por_producto(self, request):
        query = self.get_queryset().values('id_producto__nombre_producto').annotate(total_gastado=Sum('subtotal')).order_by('-total_gastado')
        datos = [{'producto': item['id_producto__nombre_producto'], 'gastado': item['total_gastado']} for item in query]
        return Response(datos, status=status.HTTP_200_OK)

    # CU-09 (Almacenero): Top productos más comprados en cantidad
    @action(detail=False, methods=['get'])
    def top_productos_comprados(self, request):
        query = self.get_queryset().values('id_producto__nombre_producto').annotate(cantidad_total=Sum('cantidad')).order_by('-cantidad_total')[:5]
        datos = [{'producto': item['id_producto__nombre_producto'], 'cantidad': item['cantidad_total']} for item in query]
        return Response(datos, status=status.HTTP_200_OK)

    # CU-10 (Almacenero): Productos controlados que están en pedidos pendientes
    @action(detail=False, methods=['get'])
    def productos_controlados_pedidos(self, request):
        # Filtra que sea producto controlado y que la orden esté en estado 'Pendiente'
        query = self.get_queryset().filter(
            id_producto__es_controlado=True,
            id_orden__estado='Pendiente'
        ).select_related('id_producto', 'id_orden')
        
        datos = [{'orden': det.id_orden.codigo_orden, 'producto_controlado': det.id_producto.nombre_producto, 'cantidad': det.cantidad} for det in query]
        return Response(datos, status=status.HTTP_200_OK)


class RecepcionPedidoViewSet(SoftDeleteModelViewSet):
    queryset = RecepcionPedido.objects.all()
    serializer_class = RecepcionPedidoSerializer
    lookup_field = 'codigo_recepcion'

    # Consulta Genérica 6: Recepciones sin factura adjunta
    @action(detail=False, methods=['get'])
    def sin_factura(self, request):
        query = self.get_queryset().filter(factura_numero__isnull=True)
        datos = [{'codigo_recepcion': rec.codigo_recepcion, 'orden': rec.id_orden.codigo_orden, 'fecha': rec.fecha_recepcion} for rec in query]
        return Response(datos, status=status.HTTP_200_OK)

    # Consulta Genérica 7: Pedidos recibidos con inconformidades (recibido_conforme=False)
    @action(detail=False, methods=['get'])
    def inconformes(self, request):
        query = self.get_queryset().filter(recibido_conforme=False)
        datos = [{'codigo_recepcion': rec.codigo_recepcion, 'orden': rec.id_orden.codigo_orden, 'observaciones': rec.observaciones_recepcion} for rec in query]
        return Response(datos, status=status.HTTP_200_OK)


class PresupuestoMensualViewSet(viewsets.ModelViewSet):
    # Nota: No usamos SoftDeleteModelViewSet aquí porque este modelo no tiene un campo 'estado', 
    # es manejado íntegramente por Finanzas y solo lo consultamos/actualizamos.
    queryset = PresupuestoMensual.objects.all()
    serializer_class = PresupuestoMensualSerializer
    lookup_field = 'periodo'

    # Consulta Genérica 8: Meses donde el presupuesto disponible es menor al 20% del asignado
    @action(detail=False, methods=['get'])
    def presupuesto_bajo(self, request):
        query = self.get_queryset().filter(monto_disponible__lt=F('monto_asignado') * 0.20)
        datos = [{'periodo': p.periodo, 'disponible': p.monto_disponible, 'asignado': p.monto_asignado} for p in query]
        return Response(datos, status=status.HTTP_200_OK)

    # Consulta Genérica 9: Resumen de todos los periodos y su ejecución (Gasto real)
    @action(detail=False, methods=['get'])
    def resumen_ejecucion(self, request):
        query = self.get_queryset().order_by('-periodo')
        datos = []
        for p in query:
            # Dividimos el periodo (Ej: '2026-05')
            try:
                año, mes = p.periodo.split('-')
                # Calculamos la suma de monto_total de todas las órdenes de este mes
                gasto = OrdenCompra.objects.filter(
                    fecha_orden__year=año,
                    fecha_orden__month=mes
                ).exclude(estado='Cancelada').aggregate(total=Sum('monto_total'))['total'] or 0
                
                # Actualizamos el saldo dinámicamente
                saldo_real = p.monto_asignado - gasto
                
                datos.append({
                    'periodo': p.periodo, 
                    'presupuesto_inicial': p.monto_asignado, 
                    'gasto_ejecutado': gasto,
                    'saldo_actual': saldo_real
                })
            except ValueError:
                # Por si el periodo no tiene formato válido
                datos.append({
                    'periodo': p.periodo, 
                    'presupuesto_inicial': p.monto_asignado, 
                    'gasto_ejecutado': p.monto_asignado - p.monto_disponible,
                    'saldo_actual': p.monto_disponible
                })
                
        return Response(datos, status=status.HTTP_200_OK)
