from django.db import models

# 1.- Modelo Proveedor
class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    codigo_proveedor = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=50, default='Activo')
    nombre_proveedor = models.CharField(max_length=255)
    nit_proveedor = models.CharField(max_length=50, unique=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.TextField(null=True, blank=True)
    email_contacto = models.EmailField(max_length=254, null=True, blank=True)

    def __str__(self):
        return self.nombre_proveedor

# 2.- Modelo Producto
class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    codigo_producto = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=50, default='Activo')
    nombre_producto = models.CharField(max_length=255)
    descripcion = models.TextField(null=True, blank=True)
    unidad_medida = models.CharField(max_length=50)
    es_controlado = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre_producto

# 3.- Modelo Relacional Proveedor_Producto
class ProveedorProducto(models.Model):
    id_proveedor_producto = models.AutoField(primary_key=True)
    codigo_proveedor_producto = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=50, default='Activo')
    id_proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='productos_ofrecidos')
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='proveedores')
    precio_referencial = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_actualizacion_precio = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id_proveedor.nombre_proveedor} - {self.id_producto.nombre_producto}"

# 4.- Modelo Requisicion_Interna
class RequisicionInterna(models.Model):
    id_requisicion = models.AutoField(primary_key=True)
    codigo_requisicion = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=50, default='Pendiente')
    area_solicitante = models.CharField(max_length=100)
    origen = models.CharField(max_length=100)
    mensaje_detalle = models.TextField(null=True, blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    urgencia = models.CharField(max_length=50)

    def __str__(self):
        return f"Req {self.codigo_requisicion} - {self.area_solicitante}"

# 5.- Modelo Orden_Compra
class OrdenCompra(models.Model):
    id_orden = models.AutoField(primary_key=True)
    codigo_orden = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=50, default='Emitida')
    fecha_orden = models.DateTimeField(auto_now_add=True)
    fecha_estimada_entrega = models.DateTimeField(null=True, blank=True)
    id_proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='ordenes_compra')
    id_requisicion = models.ForeignKey(RequisicionInterna, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordenes_generadas')
    monto_total = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    presupuesto_asignado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    id_validacion_financiera = models.CharField(max_length=100, null=True, blank=True)
    token_legal = models.CharField(max_length=255, null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Orden {self.codigo_orden}"

# 6.- Modelo Detalle_Orden
class DetalleOrden(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    codigo_detalle = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=50, default='Activo')
    id_orden = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name='detalles')
    id_producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='detalles_ordenes')
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    def save(self, *args, **kwargs):
        # El subtotal se calcula solo automáticamente antes de guardar en la BD
        if self.cantidad and self.precio:
            self.subtotal = self.cantidad * self.precio
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad} x {self.id_producto.nombre_producto}"

# 7.- Modelo Recepcion_Pedido
class RecepcionPedido(models.Model):
    id_recepcion = models.AutoField(primary_key=True)
    codigo_recepcion = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=50, default='Recibido')
    fecha_recepcion = models.DateTimeField(auto_now_add=True)
    id_orden = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name='recepciones')
    observaciones_recepcion = models.TextField(null=True, blank=True)
    factura_numero = models.CharField(max_length=100, null=True, blank=True)
    factura_archivo_url = models.CharField(max_length=255, null=True, blank=True)
    recibido_conforme = models.BooleanField(default=True)

    def __str__(self):
        return f"Recepción {self.codigo_recepcion} para Orden {self.id_orden.codigo_orden}"


# 8.- Presupuesto Mensual (enviado por MS Gestión Financiera al inicio de cada mes)
class PresupuestoMensual(models.Model):
    id_presupuesto = models.AutoField(primary_key=True)
    periodo = models.CharField(max_length=7, unique=True)  # Formato: YYYY-MM (ej. 2026-05)
    monto_asignado = models.DecimalField(max_digits=15, decimal_places=2)
    monto_disponible = models.DecimalField(max_digits=15, decimal_places=2)
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    observaciones = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Presupuesto {self.periodo}: {self.monto_asignado} Bs (Disponible: {self.monto_disponible} Bs)"
