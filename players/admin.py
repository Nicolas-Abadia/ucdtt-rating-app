from django.contrib import admin

from ratings.services import recompute_all_ratings
from .forms import MatchForm
from .models import Player, Match, RatingHistory


class RatingHistoryInline(admin.TabularInline):
    """
    A player's rating history, read only.

    The rows are derived: recompute_all_ratings() rebuilds them from the
    matches, so anything edited here would be overwritten.
    """

    model = RatingHistory
    readonly_fields = ("rating", "match", "player", "timestamp")
    extra = 0
    can_delete = False
    def has_add_permission(self, request, obj=None):
        return False

class PlayerAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {"fields": ["name"]}),
        ("Rating", {"fields": ["rating", "initial_rating"]}),
        ("Created Time", {"fields": ["created_date"]}),
    ]
    # rating is derived from the matches, so it is shown but not editable.
    # initial_rating is the editable knob; see EditPlayerView for why.
    readonly_fields = ["created_date", "rating"]
    ordering = ('-rating',)
    inlines = [RatingHistoryInline]
    # The list shows the rounded rating; the detail view still shows the
    # stored float, so the exact value the replay produced stays visible.
    list_display = ["name", "rating_display", "initial_rating", "created_date"]
    # rating is deliberately not a filter: it is a float, so the sidebar
    # would render one entry per distinct rating in the database.
    list_filter = ["created_date"]
    search_fields = ["name"]

    @admin.display(description="Rating", ordering="rating")
    def rating_display(self, obj):
        return obj.display_rating

    def save_model(self, request, obj, form, change):
        """
        Changing initial_rating changes the starting point of the replay,
        so ratings have to be rebuilt for it to mean anything.
        """
        super().save_model(request, obj, form, change)
        if "initial_rating" in form.changed_data:
            recompute_all_ratings()

class MatchAdmin(admin.ModelAdmin):
    # Reuse the same form as LogMatchView so admin edits get the no-tie and
    # no-future-date rules too. Without this the admin only enforces what the
    # database constraints cover: distinct players and non-negative scores.
    form = MatchForm
    fieldsets = [
        (None, {"fields": ["player1", "player2"]}),
        ("Score", {"fields": ["score1", "score2"]}),
        ("Date", {"fields": ["date"]})
    ]
    list_display = ["id", "player1", "player2", "score1","score2", "date"]
    list_display_links = ["player1", "player2"]
    list_filter = ["date"]
    search_fields = ["player1__name", "player2__name"]

    def delete_queryset(self, request, queryset):
        """
        The admin's bulk "delete selected" action calls queryset.delete(),
        which bypasses Match.delete() and its rating recompute. Delete the
        batch, then recompute once for the whole thing.
        """
        super().delete_queryset(request, queryset)
        recompute_all_ratings()

admin.site.register(Player, PlayerAdmin)
admin.site.register(Match, MatchAdmin)
