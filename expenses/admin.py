from django.contrib import admin

from .models import Trip, Member, Expense, Settlement


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('name', 'destination', 'created_by', 'start_date', 'end_date', 'created_at')
    search_fields = ('name', 'destination', 'created_by__username')


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'trip', 'user')
    search_fields = ('name', 'trip__name')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'trip', 'amount', 'paid_by', 'date')
    list_filter = ('trip',)
    search_fields = ('title', 'trip__name')


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ('trip', 'from_member', 'to_member', 'amount', 'settled_on')
    list_filter = ('trip',)
