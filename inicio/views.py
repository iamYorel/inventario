from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from almacenes.models import Almacen
from articulos.models import Articulo
from detalles_movimiento.stock import lotes_con_stock
from lotes.models import Lote
from movimientos.models import Movimiento


class InicioView(LoginRequiredMixin, TemplateView):
    """Panel de inicio: totales, stock por lote y últimos movimientos."""
    template_name = 'inicio/inicio.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_almacenes'] = Almacen.objects.count()
        ctx['total_articulos'] = Articulo.objects.count()
        ctx['total_lotes'] = Lote.objects.count()
        ctx['total_movimientos'] = Movimiento.objects.count()
        ctx['lotes'] = (lotes_con_stock()
                        .order_by('fk_ubi__fk_alm__alm_nombre', 'fk_art__art_nombre'))
        ctx['ultimos'] = Movimiento.objects.order_by('-mov_fecha', '-pk_mov_id')[:5]
        return ctx
