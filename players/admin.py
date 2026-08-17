from django.contrib import admin

from .models import Player, Match

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

class MatchAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ["player1", "player2"]}),
        ("Score", {"fields": ["score1", "score2"]}),
        ("Date", {"fields": ["date"]})
    ]
    list_display = ["id", "player1", "player2", "score1","score2", "date"]
    list_display_links = ["player1", "player2"]
    list_filter = ["date"]
    search_fields = ["player1__name", "player2__name"]

admin.site.register(Player, PlayerAdmin)
admin.site.register(Match, MatchAdmin)
