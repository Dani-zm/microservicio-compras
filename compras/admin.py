from django.contrib import admin
from .models import (
    Proveedor, Producto, ProveedorProducto, 
    RequisicionInterna, OrdenCompra, DetalleOrden, RecepcionPedido
)


admin.site.register(Proveedor)
admin.site.register(Producto)
admin.site.register(ProveedorProducto)
admin.site.register(RequisicionInterna)
admin.site.register(OrdenCompra)
admin.site.register(DetalleOrden)
admin.site.register(RecepcionPedido)
