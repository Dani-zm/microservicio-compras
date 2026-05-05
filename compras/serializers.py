from rest_framework import serializers
from .models import Proveedor, Producto, ProveedorProducto, RequisicionInterna, OrdenCompra, DetalleOrden

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            'codigo_proveedor', 
            'nombre_proveedor', 
            'nit_proveedor', 
            'telefono', 
            'direccion', 
            'email_contacto'
        ]

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = [
            'codigo_producto', 
            'nombre_producto', 
            'descripcion', 
            'unidad_medida', 
            'es_controlado'
        ]

class ProveedorProductoSerializer(serializers.ModelSerializer):
    codigo_proveedor = serializers.SlugRelatedField(
        slug_field='codigo_proveedor',
        queryset=Proveedor.objects.filter(estado='Activo'),
        source='id_proveedor' 
    )
    codigo_producto = serializers.SlugRelatedField(
        slug_field='codigo_producto',
        queryset=Producto.objects.filter(estado='Activo'),
        source='id_producto' 
    )

    class Meta:
        model = ProveedorProducto
        fields = [
            'codigo_proveedor_producto', 
            'codigo_proveedor', 
            'codigo_producto', 
            'precio_referencial', 
            'fecha_actualizacion_precio'
        ]

class RequisicionInternaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequisicionInterna
        fields = [
            'codigo_requisicion',
            'area_solicitante',
            'origen',
            'mensaje_detalle',
            'fecha_solicitud',
            'urgencia'
        ]

class OrdenCompraSerializer(serializers.ModelSerializer):
    codigo_proveedor = serializers.SlugRelatedField(
        slug_field='codigo_proveedor',
        queryset=Proveedor.objects.exclude(estado='Inactivo'),
        source='id_proveedor'
    )
    codigo_requisicion = serializers.SlugRelatedField(
        slug_field='codigo_requisicion',
        queryset=RequisicionInterna.objects.exclude(estado='Inactivo'),
        source='id_requisicion',
        required=False,
        allow_null=True
    )
    # Estos campos son opcionales. Si el formulario HTML los deja en blanco,
    # se convierten a null (None) en la BD en lugar de guardarse como ""
    id_validacion_financiera = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None
    )
    token_legal = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None
    )
    presupuesto_asignado = serializers.DecimalField(
        max_digits=15, decimal_places=2,
        required=False, allow_null=True, default=None
    )
    observaciones = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=None
    )

    def validate_id_validacion_financiera(self, value):
        """Convierte string vacía a None para que isnull=True funcione correctamente."""
        return None if value == '' else value

    def validate_token_legal(self, value):
        """Convierte string vacía a None para que isnull=True funcione correctamente."""
        return None if value == '' else value

    def validate_observaciones(self, value):
        """Convierte string vacía a None."""
        return None if value == '' else value

    class Meta:
        model = OrdenCompra
        fields = [
            'codigo_orden',
            'fecha_orden',
            'fecha_estimada_entrega',
            'codigo_proveedor',
            'codigo_requisicion',
            'monto_total',
            'presupuesto_asignado',
            'id_validacion_financiera',
            'token_legal',
            'observaciones'
        ]

class DetalleOrdenSerializer(serializers.ModelSerializer):
    codigo_orden = serializers.SlugRelatedField(
        slug_field='codigo_orden',
        queryset=OrdenCompra.objects.exclude(estado='Inactivo').exclude(id_proveedor__estado='Inactivo'),
        source='id_orden'
    )
    codigo_producto = serializers.SlugRelatedField(
        slug_field='codigo_producto',
        queryset=Producto.objects.exclude(estado='Inactivo'),
        source='id_producto'
    )

    class Meta:
        model = DetalleOrden
        fields = [
            'codigo_detalle',
            'codigo_orden',
            'codigo_producto',
            'cantidad',
            'precio',
            'subtotal'
        ]
