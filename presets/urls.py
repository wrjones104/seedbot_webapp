from django.urls import path
from . import views

urlpatterns = [
    path('', views.preset_list_view, name='preset-list'),
    path('my-presets/', views.my_presets_view, name='my-presets'),
    path('connect-discord/', views.connect_discord_view, name='connect-discord'),
    path('preset/new/', views.preset_create_view, name='preset-create'),
    path('preset/<path:pk>/edit/', views.preset_update_view, name='preset-edit'),
    path('preset/<path:pk>/delete/', views.preset_delete_view, name='preset-delete'),
    path('preset/<path:pk>/', views.preset_detail_view, name='preset-detail'),

    path('api/preset/<path:pk>/roll/', views.roll_seed_api_view, name='roll-seed-api'),
    path('api/preset/<path:pk>/toggle-feature/', views.toggle_feature_view, name='toggle-feature'),
]