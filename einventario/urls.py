from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.views.generic import TemplateView

def admin_divergencias_redirect(request):
    return redirect('inventarios:relatorio_divergencias')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('vistoria/', include('mobile.urls')),
    path('inventarios/', include('inventarios.urls')),
    path('admin/patrimonio/bem/divergencias/', admin_divergencias_redirect, name='admin_divergencias_redirect'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)