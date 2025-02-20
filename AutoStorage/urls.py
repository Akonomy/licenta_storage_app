"""AutoStorage URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include


from django.conf import settings
from django.conf.urls.static import static





urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),  # aplicația principală
    path('account/', include('apps.accounts.urls')),  # aplicația principală
    path('inventory/', include('apps.inventory.urls')),
    path('robot/', include('apps.robot_interface.urls')),
    path('games/', include('apps.games.urls')),
    path('storeold/', include('apps.store.urls')),
    path('store/', include('apps.store_new.urls', namespace='store_new')),

    
]


# if settings.DEBUG:  # Doar în modul de dezvoltare
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
