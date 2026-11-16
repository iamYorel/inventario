from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DeleteView, DetailView, ListView

from .forms import DetalleFormSet, MovimientoForm
from .models import Movimiento


class AccesoMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Exige sesión iniciada y los permisos de Django del rol del usuario.
    Sin sesión redirige al login; con sesión pero sin permiso, responde 403."""


PERMISOS_DETALLE = ('detalles_movimiento.add_detallemovimiento',
                    'detalles_movimiento.change_detallemovimiento',
                    'detalles_movimiento.delete_detallemovimiento')


class MovimientoListView(AccesoMixin, ListView):
    """Listar: historial de movimientos con filtro por tipo y búsqueda."""
    model = Movimiento
    permission_required = 'movimientos.view_movimiento'
    template_name = 'movimientos/lista.html'
    context_object_name = 'movimientos'
    paginate_by = 10

    def get_queryset(self):
        qs = (Movimiento.objects.annotate(num_lineas=Count('detalles'))
              .order_by('-mov_fecha', '-pk_mov_id'))
        tipo = self.request.GET.get('tipo', '')
        q = self.request.GET.get('q', '').strip()
        if tipo in (Movimiento.ENTRADA, Movimiento.SALIDA):
            qs = qs.filter(mov_tipo=tipo)
        if q:
            filtro = Q(mov_observacion__icontains=q)
            if q.isdigit():
                filtro |= Q(pk_mov_id=int(q))
            qs = qs.filter(filtro)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx['querystring'] = params.urlencode()
        ctx['tipo'] = self.request.GET.get('tipo', '')
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class MovimientoDetailView(AccesoMixin, DetailView):
    """Detalle: el movimiento con sus lotes, artículos y ubicaciones."""
    model = Movimiento
    permission_required = 'movimientos.view_movimiento'
    template_name = 'movimientos/detalle.html'
    context_object_name = 'movimiento'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['detalles'] = (self.object.detalles
                           .select_related('fk_lot__fk_art',
                                           'fk_lot__fk_ubi__fk_alm')
                           .order_by('pk_det_id'))
        return ctx


class MovimientoFormularioView(AccesoMixin, View):
    """Base de Crear y Editar: un formulario de movimiento más el formset de
    sus líneas (lote + cantidad), guardados juntos en una transacción."""
    template_name = 'movimientos/formulario.html'
    titulo = ''

    def get_movimiento(self):
        return None

    def armar(self, datos=None):
        movimiento = self.get_movimiento()
        if datos is None:
            inicial = {'mov_fecha': timezone.localdate()} if not movimiento else None
            form = MovimientoForm(instance=movimiento, initial=inicial)
        else:
            form = MovimientoForm(datos, instance=movimiento)
        # el formset valida con el tipo del movimiento: se arma con la misma
        # instancia, que el formulario completa al validarse
        formset = DetalleFormSet(datos, instance=form.instance)
        return form, formset

    def mostrar(self, request, form, formset):
        return render(request, self.template_name, {
            'form': form, 'formset': formset, 'titulo': self.titulo,
            'movimiento': form.instance if form.instance.pk else None})

    def get(self, request, *args, **kwargs):
        form, formset = self.armar()
        return self.mostrar(request, form, formset)

    def post(self, request, *args, **kwargs):
        form, formset = self.armar(request.POST)
        form_ok = form.is_valid()          # primero el formulario: fija el tipo
        formset_ok = formset.is_valid()
        if form_ok and formset_ok:
            try:
                with transaction.atomic():
                    movimiento = form.save()
                    formset.save()
            except (ValidationError, IntegrityError) as error:
                detalle = (' '.join(error.messages)
                           if isinstance(error, ValidationError)
                           else 'Hay líneas repetidas o inválidas.')
                messages.error(request, f'No se guardó el movimiento. {detalle}')
                form, formset = self.armar(request.POST)  # instancias limpias
            else:
                messages.success(request, self.mensaje_ok.format(movimiento.pk_mov_id))
                return redirect('movimientos:detalle', pk=movimiento.pk_mov_id)
        else:
            messages.error(request, 'Revisa los campos marcados en rojo.')
        return self.mostrar(request, form, formset)


class MovimientoCrearView(MovimientoFormularioView):
    """Crear: registrar una entrada o salida con sus lotes y cantidades."""
    permission_required = ('movimientos.add_movimiento',
                           'detalles_movimiento.add_detallemovimiento')
    titulo = 'Registrar movimiento'
    mensaje_ok = 'Movimiento #{} registrado.'


class MovimientoEditarView(MovimientoFormularioView):
    """Editar: fecha, observación y líneas (el tipo no cambia)."""
    permission_required = ('movimientos.change_movimiento',) + PERMISOS_DETALLE
    titulo = 'Editar movimiento'
    mensaje_ok = 'Movimiento #{} actualizado.'

    def get_movimiento(self):
        return get_object_or_404(Movimiento, pk=self.kwargs['pk'])


class MovimientoEliminarView(AccesoMixin, DeleteView):
    """Eliminar: pide confirmación y respeta las reglas del stock."""
    model = Movimiento
    permission_required = ('movimientos.delete_movimiento',
                           'detalles_movimiento.delete_detallemovimiento')
    template_name = 'movimientos/confirmar_eliminar.html'
    context_object_name = 'movimiento'
    success_url = reverse_lazy('movimientos:lista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['num_lineas'] = self.object.detalles.count()
        return ctx

    def form_valid(self, form):
        numero = self.object.pk_mov_id
        try:
            with transaction.atomic():
                self.object.delete()
        except ValidationError as error:
            # p. ej. borrar una entrada cuyo stock ya se consumió
            messages.error(self.request,
                           f'No se eliminó el movimiento #{numero}. '
                           + ' '.join(error.messages))
            return redirect(reverse('movimientos:detalle', kwargs={'pk': numero}))
        messages.success(self.request, f'Movimiento #{numero} eliminado.')
        return redirect(self.success_url)
