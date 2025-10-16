from django.contrib import admin
from rest_framework.authtoken.models import Token
from .models import Profile


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created')
    fields = ('user', 'key', 'created')
    readonly_fields = ('user', 'key', 'created')
    actions = ['regenerate_token']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        if obj and obj.user == request.user:
            return True
        return request.user.is_superuser
    
    @admin.action(description='Regenerate token')
    def regenerate_token(self, request, queryset):
        for token in queryset:
            if request.user.is_superuser or token.user == request.user:
                token.delete()
                Token.objects.create(user=token.user)
        self.message_user(request, f"Regenerated {queryset.count()} token(s)")


admin.site.register(Profile)
