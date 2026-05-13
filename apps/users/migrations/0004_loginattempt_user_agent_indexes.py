# Generated manually — RF05 Auditoría de Login
# Agrega campo user_agent e índices de rendimiento a la tabla login_logs

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_customuser_photo"),
    ]

    operations = [
        # 1. Agregar campo user_agent para capturar la herramienta/navegador del cliente
        migrations.AddField(
            model_name="loginattempt",
            name="user_agent",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Agente de usuario del cliente (navegador o herramienta).",
                max_length=512,
                verbose_name="User-Agent",
            ),
        ),
        # 2. Índice compuesto para consultas de brute-force por IP
        migrations.AddIndex(
            model_name="loginattempt",
            index=models.Index(
                fields=["ip_address", "-timestamp"],
                name="idx_login_ip_ts",
            ),
        ),
        # 3. Índice para filtrar intentos fallidos/exitosos con ordenamiento
        migrations.AddIndex(
            model_name="loginattempt",
            index=models.Index(
                fields=["was_successful", "-timestamp"],
                name="idx_login_success_ts",
            ),
        ),
    ]
