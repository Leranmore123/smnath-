from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='login'), # Land on login page by default
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # User Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Wallet & Topups
    path('wallet/', views.wallet, name='wallet'),
    path('wallet/history/', views.wallet_history, name='wallet_history'),
    
    # Services
    path('services/<slug:category_slug>/', views.services_list, name='services_list'),
    path('apply/<slug:service_slug>/', views.apply_service, name='apply_service'),
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('user/rc_wotp_short_rc.php', views.rc_wotp_short_rc, name='rc_wotp_short_rc'),
    path('user/pan_card_print/', views.pan_card_print, name='pan_card_print'),
    path('pan_card_print/', views.pan_card_print, name='pan_card_print_root'),
    path('apply/otp/<int:app_id>/', views.verify_otp_view, name='verify_otp'),
    path('api/govt-submission-bot/', views.govt_submission_bot_api, name='govt_submission_bot'),

    # Profile & Static Pages
    path('profile/', views.profile_view, name='profile'),
    path('profile/password/', views.change_password, name='change_password'),
    path('pricing/', views.pricing, name='pricing'),
    path('faq/', views.faq, name='faq'),
    
    # Custom Staff Panel
    path('staff/dashboard/', views.admin_panel, name='admin_panel'),
    path('staff/topup/approve/<int:topup_id>/', views.admin_approve_topup, name='admin_approve_topup'),
    path('staff/topup/reject/<int:topup_id>/', views.admin_reject_topup, name='admin_reject_topup'),
    path('staff/application/complete/<int:app_id>/', views.admin_complete_application, name='admin_complete_application'),
    path('staff/application/reject/<int:app_id>/', views.admin_reject_application, name='admin_reject_application'),
    path('api/fetch-pan-details/', views.fetch_pan_details, name='fetch_pan_details'),
]
