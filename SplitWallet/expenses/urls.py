from django.urls import path
from . import views
from .views import CustomPasswordResetView, CustomPasswordResetDoneView, CustomPasswordResetConfirmView, CustomPasswordResetCompleteView

urlpatterns = [
    path('', views.home, name='home'),
    
    path('login/', views.user_login, name='login'),
    path('profile/', views.user_profile, name='profile'),
    path('settings/', views.user_settings, name='settings'),
    
    path('event/<int:event_id>/settlement/', views.settlement, name='settlement'),
    
    path('analytics/', views.analytics, name='analytics'),
    path('analytics_data/', views.analytics_data, name='analytics_data'),
    path('analytics_data_by_month/', views.analytics_data_by_month, name='analytics_data_by_month'),
    path('analytics_data_by_year/', views.analytics_data_by_year, name='analytics_data_by_year'),
    
    path('expense_by_category/', views.expense_by_category, name='expense_by_category'),
    path('percentage_by_category/', views.percentage_by_category, name='percentage_by_category'),
    path('expense_and_event_by_month_and_day/', views.expense_and_event_by_month_and_day, name='expense_and_event_by_month_and_day'),
    
    path('signup/', views.user_signup, name='signup'),
    path('account_activation/<str:uidb64>/<str:token>/', views.account_activation, name='account_activation'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('logout/', views.user_logout, name='logout'),
    
    # Custom Password Reset URLs
    path('password_reset/', CustomPasswordResetView.as_view(), name='custom_password_reset'),
    path('password_reset/done/', CustomPasswordResetDoneView.as_view(), name='custom_password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='custom_password_reset_confirm'),
    path('reset/done/', CustomPasswordResetCompleteView.as_view(), name='custom_password_reset_complete'),
    
    path('create_event/', views.create_event, name='create_event'),
    path('event/<int:event_id>/', views.event_details, name='event_details'),
    path('event/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('event/<int:event_id>/add_member/', views.add_member, name='add_member'),
    
    path('event/<int:event_id>/members/', views.members, name='members'),
    path('event/<int:event_id>/edit_member/<int:member_id>/', views.edit_member, name='edit_member'),
    path('event/<int:event_id>/delete_member/<int:member_id>/', views.delete_member, name='delete_member'),
    
    path('expense/<int:expense_id>/', views.expense_detail, name='expense_detail'),
    path('expense/<int:expense_id>/edit/', views.edit_expense, name='edit_expense'),
    path('expense/<int:expense_id>/delete/', views.delete_expense, name='delete_expense'),
    path('event/<int:event_id>/generate_report/', views.generate_report, name='generate_report'),
    path('expense/<int:event_id>/audit_trail/', views.expense_audit_trail, name='expense_audit_trail'),
    
    path('category_distribution/<int:event_id>/', views.category_distribution_view, name='category_distribution'),
    path('selected_user_expenses/<int:event_id>/<int:user_id>/', views.selected_user_expense_view, name='selected_user_expenses'),

]
