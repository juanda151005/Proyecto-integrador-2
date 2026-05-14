import re

from rest_framework import serializers

from .models import Client, Plan


class PlanSerializer(serializers.ModelSerializer):
    """Serializer completo para el modelo Plan."""

    class Meta:
        model = Plan
        fields = [
            "id",
            "code",
            "name",
            "description",
            "target_plan_name",
            "target_plan_price",
            "min_seniority_days",
            "message_template_whatsapp",
            "message_template_sms",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClientSerializer(serializers.ModelSerializer):
    """Serializer completo de lectura para Client."""

    plan_detail = PlanSerializer(source="plan", read_only=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "phone_number",
            "full_name",
            "document_number",
            "email",
            "activation_date",
            "current_plan",
            "plan",
            "plan_detail",
            "is_eligible",
            "average_spending",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_eligible",
            "average_spending",
            "created_at",
            "updated_at",
        ]


class ClientCreateSerializer(serializers.ModelSerializer):
    """Serializer para creación de clientes prepago (RF06)."""

    class Meta:
        model = Client
        fields = [
            "id",
            "phone_number",
            "full_name",
            "document_number",
            "email",
            "activation_date",
            "current_plan",
            "plan",
        ]
        read_only_fields = ["id"]

    def validate_phone_number(self, value):
        """Valida formato colombiano: 10 dígitos, empieza con 3."""
        if not re.match(r"^3\d{9}$", value):
            raise serializers.ValidationError(
                "El número debe tener 10 dígitos y empezar con 3. Ej: 3001234567"
            )
        return value


class ClientUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualización de clientes (RF08).
    Bloquea cambios a phone_number y document_number (datos de identidad).
    """

    class Meta:
        model = Client
        fields = [
            "id",
            "phone_number",
            "full_name",
            "document_number",
            "email",
            "activation_date",
            "current_plan",
            "plan",
            "is_eligible",
            "average_spending",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "phone_number",
            "document_number",
            "is_eligible",
            "average_spending",
            "created_at",
            "updated_at",
        ]


class ClientExportSerializer(serializers.ModelSerializer):
    """Serializer para exportación a CSV (RF10)."""

    plan_code = serializers.CharField(source="plan.code", read_only=True, default="")

    class Meta:
        model = Client
        fields = [
            "phone_number",
            "full_name",
            "document_number",
            "email",
            "activation_date",
            "current_plan",
            "plan_code",
            "is_eligible",
            "average_spending",
            "status",
        ]


class ClientImportRowSerializer(serializers.Serializer):
    """
    Validador por fila para importación masiva de clientes (CSV/Excel).

    Columnas esperadas (en orden):
        1. numero_celular    — str, 10 dígitos, empieza en 3
        2. nombre_completo   — str
        3. numero_documento  — str, máx 20 chars
        4. correo            — email (opcional)
        5. fecha_activacion  — YYYY-MM-DD o DD/MM/YYYY
        6. codigo_plan       — str, referencia a Plan.code (opcional)
    """

    numero_celular = serializers.CharField(max_length=20)
    nombre_completo = serializers.CharField(max_length=200)
    numero_documento = serializers.CharField(max_length=20)
    correo = serializers.EmailField(required=False, allow_blank=True, default="")
    fecha_activacion = serializers.DateField(
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
    )
    codigo_plan = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )

    def validate_numero_celular(self, value):
        if not re.match(r"^3\d{9}$", str(value).strip()):
            raise serializers.ValidationError(
                "Formato inválido. Debe tener 10 dígitos y empezar con 3."
            )
        return str(value).strip()
