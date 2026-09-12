from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from modules.contact.models import ContactMessage, MessageStatus


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "status", "delivery_state", "created_at")
    list_filter = ("status", "delivered", "locale", "created_at")
    search_fields = ("name", "email", "subject", "message")
    date_hierarchy = "created_at"
    readonly_fields = (
        "name",
        "email",
        "subject",
        "message",
        "locale",
        "ip_hash",
        "user_agent",
        "delivered",
        "created_at",
        "updated_at",
    )
    actions = ("mark_read", "mark_replied", "mark_spam")

    def has_add_permission(self, request) -> bool:
        return False

    @admin.display(description="Notificación")
    def delivery_state(self, obj: ContactMessage) -> str:
        if obj.status == MessageStatus.SPAM:
            return format_html('<span style="color:#6b7280">no enviada (spam)</span>')
        if obj.delivered:
            return format_html('<span style="color:#16a34a">✓ enviada</span>')
        return format_html('<span style="color:#dc2626">✗ falló el envío</span>')

    @admin.action(description="Marcar como leído")
    def mark_read(self, request, queryset) -> None:
        queryset.update(status=MessageStatus.READ)

    @admin.action(description="Marcar como respondido")
    def mark_replied(self, request, queryset) -> None:
        queryset.update(status=MessageStatus.REPLIED)

    @admin.action(description="Marcar como spam")
    def mark_spam(self, request, queryset) -> None:
        queryset.update(status=MessageStatus.SPAM)
