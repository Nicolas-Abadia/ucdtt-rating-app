from django.contrib import admin

from .models import Player

# Register your models here.

class PlayerAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ["name"]}),
        ("Rating", {"fields": ["rating"]}),
        ("Created Time", {"fields": ["created_date"]}),
    ]
    readonly_fields = ["created_date"]
    list_display = ["name", "rating", "created_date"]
    list_filter = ["rating", "created_date"]
    search_fields = ["name"]


admin.site.register(Player, PlayerAdmin)
