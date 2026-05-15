from django.utils import timezone
from rest_framework import serializers

from apps.core_business.models import Client


class ProspectSerializer(serializers.ModelSerializer):
    """
    RF20 — Serializer de solo lectura para prospectos expuestos a sistemas externos.
    Orientado a integración con CRM: no expone datos sensibles internos.
    """

    plan_code = serializers.CharField(source="plan.code", read_only=True, default=None)
    plan_name = serializers.CharField(source="plan.name", read_only=True, default=None)
    seniority_days = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            "id",
            "phone_number",
            "full_name",
            "current_plan",
            "plan_code",
            "plan_name",
            "is_eligible",
            "average_spending",
            "seniority_days",
            "status",
            "activation_date",
            "created_at",
        ]

    def get_seniority_days(self, obj):
        return (timezone.localdate() - obj.activation_date).days
