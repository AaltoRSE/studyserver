from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Study, Consent
from .forms import StudyAdminForm

@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = (
        'study',
        'participant_username',
        'source_type',
        'data_source_status',
        'is_complete',
        'consent_date'
    )
    researcher_readonly_fields = (
        'study',
        'participant',
        'source_type',
        'data_source',
        'consent_text_accepted',
        'is_complete',
        'consent_date',
        'revocation_date'
    )

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ('participant', 'study', 'source_type', 'consent_date')
        return self.researcher_readonly_fields


    @admin.display(description='Participant')
    def participant_username(self, obj):
        return obj.participant.user.username
    
    @admin.display(description='Source Status')
    def data_source_status(self, obj):
        if not obj.data_source:
            return "Not linked"
        source = obj.data_source.get_real_instance()
        return f"{source.name} ({source.status})"


class ConsentInline(admin.TabularInline):
    model = Consent
    list_display = ('participant_username', 'consent_date', 'revocation_date', 'is_complete')
    readonly_fields = (
        'participant_username',
        'source_type',
        'data_source_info',
        'consent_text_accepted',
        'is_complete',
        'consent_date',
        'revocation_date',
        'data_actions'
    )
    fields = (
        'participant_username',
        'source_type',
        'data_source_info',
        'is_complete',
        'data_actions'
    )
    can_delete = False
    extra = 0

    @admin.display(description='Participant')
    def participant_username(self, obj):
        return obj.participant.user.username
    
    @admin.display(description='Data Source')
    def data_source_info(self, obj):
        if not obj.data_source:
            return "Not linked"
        source = obj.data_source.get_real_instance()
        status_color = 'green' if source.status == 'active' else 'orange'
        return format_html(
            '<span style="color: {};">{}</span> ({})',
            status_color,
            source.name,
            source.status
        )
    
    @admin.display(description='Actions')
    def data_actions(self, obj):
        if not obj.data_source or obj.data_source.status != 'active':
            return "-"
        
        download_url = reverse('admin_download_consent_data', args=[obj.id])
        return format_html(
            '<a href="{}">Download Data</a>',
            download_url
        )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Study)
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

