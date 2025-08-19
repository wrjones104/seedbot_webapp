# presets/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # --- Non-PK routes first ---
    path('', views.preset_list_view, name='preset-list'),
    path('my-presets/', views.my_presets_view, name='my-presets'),
    path('create/', views.preset_create_view, name='preset-create'),
    path('roll-status/<str:task_id>/', views.get_local_seed_roll_status_view, name='get-local-seed-roll-status'),

    # --- Routes that use the preset's PK ---
    path('<path:pk>/update/', views.preset_update_view, name='preset-update'),
    path('<path:pk>/delete/', views.preset_delete_view, name='preset-delete'),
    path('<path:pk>/toggle-feature/', views.toggle_feature_view, name='toggle-feature'),
    path('<path:pk>/toggle-favorite/', views.toggle_favorite_view, name='toggle-favorite'),
    
    # This is now the single endpoint for all seed rolling
    path('<path:pk>/roll/', views.roll_seed_dispatcher_view, name='roll-seed'),
    
    # The general "catch-all" for a preset name comes last.
    path('<path:pk>/', views.preset_detail_view, name='preset-detail'),
]