from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserProfile, Service, ServiceApplication, TopupRequest

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_wallet_balance', 'get_status', 'is_staff')
    
    def get_wallet_balance(self, instance):
        if hasattr(instance, 'profile'):
            return instance.profile.wallet_balance
        return 0.00
    get_wallet_balance.short_description = 'Wallet Balance'
    
    def get_status(self, instance):
        if hasattr(instance, 'profile'):
            return instance.profile.status
        return 'Active'
    get_status.short_description = 'Status'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'subcategory', 'cost', 'service_type', 'is_active')
    list_filter = ('category', 'subcategory', 'service_type', 'is_active')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(ServiceApplication)
class ServiceApplicationAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'service', 'amount', 'status', 'created_at')
    list_filter = ('status', 'service__category', 'created_at')
    search_fields = ('order_id', 'user__username', 'service__name')
    readonly_fields = ('order_id', 'amount', 'balance_before', 'balance_after', 'created_at', 'updated_at')

@admin.register(TopupRequest)
class TopupRequestAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'amount', 'status', 'transaction_id_utr', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_id', 'user__username', 'transaction_id_utr')
    readonly_fields = ('order_id', 'amount', 'balance_before', 'balance_after', 'created_at', 'updated_at')
    actions = ['approve_topups', 'reject_topups']
    
    def approve_topups(self, request, queryset):
        approved_count = 0
        for obj in queryset:
            if obj.status == 'PENDING':
                profile = obj.user.profile
                obj.balance_before = profile.wallet_balance
                profile.wallet_balance += obj.amount
                profile.save()
                obj.balance_after = profile.wallet_balance
                obj.status = 'APPROVED'
                obj.save()
                approved_count += 1
        self.message_user(request, f"{approved_count} topups have been APPROVED.")
    approve_topups.short_description = "Approve selected topups (credit user wallet)"

    def reject_topups(self, request, queryset):
        updated = queryset.filter(status='PENDING').update(status='REJECTED')
        self.message_user(request, f"{updated} topups have been REJECTED.")
    reject_topups.short_description = "Reject selected topups"
