from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProveedorViewSet, ProductoViewSet, ProveedorProductoViewSet,
    RequisicionInternaViewSet, OrdenCompraViewSet, DetalleOrdenViewSet
)

router = DefaultRouter()
router.register(r'proveedores', ProveedorViewSet, basename='proveedor')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'proveedor-productos', ProveedorProductoViewSet, basename='proveedorproducto')
router.register(r'requisiciones', RequisicionInternaViewSet, basename='requisicion')
router.register(r'ordenes', OrdenCompraViewSet, basename='orden')
router.register(r'detalles-orden', DetalleOrdenViewSet, basename='detalleorden')

urlpatterns = [
    path('', include(router.urls)),
]
