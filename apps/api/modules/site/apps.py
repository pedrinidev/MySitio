from django.apps import AppConfig


class SiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.site"
    label = "site_content"
    verbose_name = "Perfil y CV"
