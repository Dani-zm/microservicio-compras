from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Exists, OuterRef, F
from django.utils import timezone
import requests as http_requests

from .models import Proveedor, Producto, ProveedorProducto, RequisicionInterna, OrdenCompra, DetalleOrden
from .serializers import (
    ProveedorSerializer, ProductoSerializer, ProveedorProductoSerializer,
    RequisicionInternaSerializer, OrdenCompraSerializer, DetalleOrdenSerializer
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


class OrdenCompraViewSet(SoftDeleteModelViewSet):
    queryset = OrdenCompra.objects.all()
    serializer_class = OrdenCompraSerializer
    lookup_field = 'codigo_orden'
    # Consulta Genérica 4: Búsqueda Filtrada 

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

        # Toma el primer producto controlado para la solicitud
        detalle = detalles_controlados.first()
        nombre_producto = detalle.id_producto.nombre_producto

        payload = {
            "Codigo": orden.codigo_orden,
            "TipoSolicitud": "Narcotico",
            "Motivo": "Compra de fármaco controlado - Proceso hospitalario",
            "Descripcion": f"Producto: {nombre_producto} | Cantidad: {detalle.cantidad} | Orden: {orden.codigo_orden}",
            "FechaSolicitud": str(timezone.now().date())
        }

        try:
            respuesta = http_requests.post(
                MS_LEGAL_SOLICITAR_TOKEN,
                params=payload,   # Legal usa query params según su Swagger
                timeout=10
            )

            if respuesta.status_code in [200, 201]:
                datos_legal = respuesta.json() if respuesta.content else {}
                token_recibido = datos_legal.get('token', datos_legal.get('Token', orden.codigo_orden + '-LEGAL-OK'))

                # Guarda el token en la orden
                orden.token_legal = str(token_recibido)
                orden.save(update_fields=['token_legal'])

                return Response({
                    'mensaje': f'Aprobación legal obtenida para {nombre_producto}',
                    'token_legal': orden.token_legal,
                    'respuesta_legal': datos_legal
                }, status=status.HTTP_200_OK)
            else:
                orden.observaciones = f'Token legal rechazado por Gestión Legal. Código: {respuesta.status_code}'
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
        query = self.get_queryset().filter(id_producto__es_controlado=True).select_related('id_producto', 'id_orden')
        datos = [{'orden': det.id_orden.codigo_orden, 'producto_controlado': det.id_producto.nombre_producto, 'cantidad': det.cantidad} for det in query]
        return Response(datos, status=status.HTTP_200_OK)
