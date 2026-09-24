from django.urls import path

from . import views 

urlpatterns = [
    path('', views.home, name='home'),

    # Movies
    path('movie/<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('movie/<int:movie_id>/shows/', views.select_show, name='select_show'),

    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Booking flow
    path('show/<int:show_id>/seats/', views.select_seats, name='select_seats'),
    path('booking/review/', views.booking_review, name='booking_review'),
    path('booking/payment/', views.payment, name='payment'),
    path('booking/success/<str:booking_id>/', views.booking_success, name='booking_success'),

    # My bookings
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('booking/<str:booking_id>/', views.booking_detail, name='booking_detail'),
    path('booking/<str:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),

    # Profile
    path('profile/', views.profile, name='profile'),
]
