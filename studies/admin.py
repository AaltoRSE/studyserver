from django.contrib import admin
from .models import Study, Consent
from .forms import StudyAdminForm


class ConsentInline(admin.TabularInline):
    """
    This creates an inline view of Consent objects.
    It will be displayed on the Study change page.
    """
    model = Consent
    list_display = ('participant_username', 'consent_date', 'revocation_date', 'is_complete')
    readonly_fields = ('participant_username', 'consent_date', 'revocation_date', 'is_complete', 'participant', 'data_source')
    can_delete = False
    extra = 0

    @admin.display(description='Participant')
    def participant_username(self, obj):
        return obj.participant.user.username

    def has_add_permission(self, request, obj=None):
        return False


class StudyAdmin(admin.ModelAdmin):
    form = StudyAdminForm
    list_display = ('title',)
    filter_horizontal = ('researchers',)
    inlines = [ConsentInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(researchers=request.user.profile)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.user = request.user
        form.base_fields['researchers'].widget.can_add_related = False
        form.base_fields['researchers'].widget.can_delete_related = False
        return form
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            obj.researchers.add(request.user.profile)


admin.site.register(Study, StudyAdmin)
admin.site.register(Consent)
