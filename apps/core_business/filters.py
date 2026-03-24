import django_filters
from django.db.models import Q

from .models import Client


class ClientFilter(django_filters.FilterSet):
    """
    Filtros de negocio para clientes (RF07).
    Permite filtrar por gasto, plan, elegibilidad, fecha, estado
    y búsqueda parcial por nombre o teléfono.
    """

    min_spending = django_filters.NumberFilter(
        field_name="average_spending", lookup_expr="gte"
    )
    max_spending = django_filters.NumberFilter(
        field_name="average_spending", lookup_expr="lte"
    )
    activation_after = django_filters.DateFilter(
        field_name="activation_date", lookup_expr="gte"
    )
    activation_before = django_filters.DateFilter(
        field_name="activation_date", lookup_expr="lte"
    )
    search = django_filters.CharFilter(
        method="filter_search",
        label="Búsqueda por nombre o teléfono",
    )

    class Meta:
        model = Client
        fields = {
            "current_plan": ["exact"],
            "is_eligible": ["exact"],
            "status": ["exact"],
            "phone_number": ["exact", "icontains"],
            "full_name": ["icontains"],
        }

    def filter_search(self, queryset, name, value):
        """Búsqueda parcial en full_name o phone_number."""
        return queryset.filter(
            Q(full_name__icontains=value) | Q(phone_number__icontains=value)
        )
