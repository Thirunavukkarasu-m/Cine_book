from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import *

SESSION_KEY = 'pending_booking'



# Helpers


def _calculate_totals(seats):
    """Recalculate pricing from the database. Never trust client-side totals."""
    from django.conf import settings

    subtotal = sum((seat.price for seat in seats), Decimal('0.00'))
    convenience_fee = Decimal(settings.CONVENIENCE_FEE) if seats else Decimal('0.00')
    total = subtotal + convenience_fee
    return subtotal, convenience_fee, total


def _get_pending_booking(request):
    """Fetch and validate the seat selection stored in the session."""
    data = request.session.get(SESSION_KEY)
    if not data:
        return None, None

    show = Show.objects.select_related('movie', 'screen', 'screen__theatre').filter(
        id=data.get('show_id')
    ).first()
    if not show:
        return None, None

    seats = list(
        Seat.objects.filter(id__in=data.get('seat_ids', []), screen=show.screen, is_active=True)
    )
    if not seats:
        return None, None

    return show, seats



# Public browsing views


def home(request):
    movies = Movie.objects.filter(is_active=True)

    search = request.GET.get('search', '').strip()
    genre = request.GET.get('genre', '').strip()
    language = request.GET.get('language', '').strip()
    sort = request.GET.get('sort', '').strip()

    if search:
        movies = movies.filter(
            Q(title__icontains=search) | Q(genre__icontains=search) | Q(language__icontains=search)
        )
    if genre:
        movies = movies.filter(genre__iexact=genre)
    if language:
        movies = movies.filter(language__iexact=language)

    sort_map = {
        'rating': '-rating',
        'newest': '-release_date',
        'title': 'title',
    }
    movies = movies.order_by(sort_map.get(sort, '-release_date'))

    genres = Movie.objects.filter(is_active=True).values_list('genre', flat=True).distinct().order_by('genre')
    languages = Movie.objects.filter(is_active=True).values_list('language', flat=True).distinct().order_by('language')

    return render(request, 'home.html', {
        'movies': movies,
        'genres': genres,
        'languages': languages,
        'search': search,
        'selected_genre': genre,
        'selected_language': language,
        'selected_sort': sort,
    })


def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id, is_active=True)
    upcoming_shows_exist = Show.objects.filter(
        movie=movie, is_active=True, show_date__gte=timezone.localdate()
    ).exists()

    return render(request, 'movie_detail.html', {
        'movie': movie,
        'upcoming_shows_exist': upcoming_shows_exist,
    })


def select_show(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id, is_active=True)

    shows = Show.objects.filter(
        movie=movie,
        is_active=True,
        show_date__gte=timezone.localdate(),
    ).select_related('screen', 'screen__theatre').order_by('show_date', 'start_time')

    # Only keep genuinely bookable (future) shows, even on today's date.
    shows = [show for show in shows if show.is_bookable]

    # Group shows by theatre for a friendlier display.
    theatres = {}
    for show in shows:
        theatre = show.screen.theatre
        theatres.setdefault(theatre, []).append(show)

    return render(request, 'select_show.html', {
        'movie': movie,
        'theatres': theatres,
    })



# Authentication


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    errors = {}
    values = {'username': '', 'email': ''}

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        values['username'] = username
        values['email'] = email

        if not username:
            errors.setdefault('username', []).append('Username is required.')
        elif len(username) > 150:
            errors.setdefault('username', []).append('Username must be at most 150 characters long.')
        elif User.objects.filter(username__iexact=username).exists():
            errors.setdefault('username', []).append('This username is already taken.')

        if not email:
            errors.setdefault('email', []).append('Email is required.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.setdefault('email', []).append('Enter a valid email address.')
            else:
                if User.objects.filter(email__iexact=email).exists():
                    errors.setdefault('email', []).append('An account with this email already exists.')

        if not password:
            errors.setdefault('password', []).append('Password is required.')
        elif len(password) < 8:
            errors.setdefault('password', []).append('Password must be at least 8 characters long.')

        if not confirm_password:
            errors.setdefault('confirm_password', []).append('Please confirm your password.')
        elif password and confirm_password and password != confirm_password:
            errors.setdefault('confirm_password', []).append('Passwords do not match.')

        if not errors:
            user = User.objects.create_user(username=username, email=email, password=password)
            auth_login(request, user)
            messages.success(request, f'Welcome to CineBook, {user.username}! Your account has been created.')
            return redirect(request.GET.get('next') or 'home')

    return render(request, 'register.html', {'errors': errors, 'values': values})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('home')

    next_url = request.POST.get('next') or request.GET.get('next', '')
    error = None
    username_value = ''

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        username_value = username

        user = authenticate(request, username=username, password=password) if username and password else None

        if user is not None:
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect(next_url or 'home')

        error = 'Please enter a correct username and password. Note that both fields may be case-sensitive.'

    return render(request, 'login.html', {'error': error, 'next': next_url, 'username_value': username_value})


@login_required
def user_logout(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')



# Seat selection & booking flow


@login_required
def select_seats(request, show_id):
    show = get_object_or_404(
        Show.objects.select_related('movie', 'screen', 'screen__theatre'),
        id=show_id,
    )

    if not show.is_bookable:
        messages.error(request, 'This show is no longer available for booking.')
        return redirect('select_show', movie_id=show.movie_id)

    seats = Seat.objects.filter(screen=show.screen, is_active=True).order_by('row_label', 'seat_number')

    booked_seat_ids = set(
        BookedSeat.objects.filter(show=show, is_cancelled=False).values_list('seat_id', flat=True)
    )

    if request.method == 'POST':
        raw_ids = request.POST.get('seat_ids', '')
        seat_ids = [int(s) for s in raw_ids.split(',') if s.strip().isdigit()]

        from django.conf import settings

        if not seat_ids:
            messages.error(request, 'Please select at least one seat.')
        elif len(seat_ids) > settings.MAX_SEATS_PER_BOOKING:
            messages.error(request, f'You can book a maximum of {settings.MAX_SEATS_PER_BOOKING} seats at a time.')
        else:
            valid_seats = Seat.objects.filter(id__in=seat_ids, screen=show.screen, is_active=True)
            if valid_seats.count() != len(set(seat_ids)):
                messages.error(request, 'One or more selected seats are invalid. Please try again.')
            else:
                already_booked = set(
                    BookedSeat.objects.filter(
                        show=show, seat_id__in=seat_ids, is_cancelled=False
                    ).values_list('seat_id', flat=True)
                )
                if already_booked:
                    messages.error(
                        request,
                        'Sorry, one or more selected seats were just booked by another customer. '
                        'Please select different seats.',
                    )
                else:
                    request.session[SESSION_KEY] = {'show_id': show.id, 'seat_ids': seat_ids}
                    return redirect('booking_review')

    return render(request, 'select_seats.html', {
        'show': show,
        'movie': show.movie,
        'seats': seats,
        'booked_seat_ids': booked_seat_ids,
    })


@login_required
def booking_review(request):
    show, seats = _get_pending_booking(request)
    if not show or not seats:
        messages.error(request, 'Your seat selection has expired. Please select your seats again.')
        return redirect('home')

    # Re-validate the show is still bookable and seats are still free.
    if not show.is_bookable:
        messages.error(request, 'This show is no longer available for booking.')
        request.session.pop(SESSION_KEY, None)
        return redirect('select_show', movie_id=show.movie_id)

    still_booked = BookedSeat.objects.filter(
        show=show, seat__in=seats, is_cancelled=False
    ).exists()
    if still_booked:
        messages.error(request, 'One or more of your selected seats have just been booked. Please choose again.')
        request.session.pop(SESSION_KEY, None)
        return redirect('select_seats', show_id=show.id)

    subtotal, convenience_fee, total = _calculate_totals(seats)

    return render(request, 'booking_review.html', {
        'show': show,
        'movie': show.movie,
        'seats': sorted(seats, key=lambda s: s.seat_number),
        'subtotal': subtotal,
        'convenience_fee': convenience_fee,
        'total': total,
    })


@login_required
def payment(request):
    show, seats = _get_pending_booking(request)
    if not show or not seats:
        messages.error(request, 'Your seat selection has expired. Please select your seats again.')
        return redirect('home')

    subtotal, convenience_fee, total = _calculate_totals(seats)
    valid_methods = dict(Payment.PAYMENT_METHODS)
    selected_method = 'DEMO'

    if request.method == 'POST':
        selected_method = request.POST.get('payment_method', '')
        simulate_failure = request.POST.get('simulate_failure') == 'on'

        if not show.is_bookable:
            messages.error(request, 'This show is no longer available for booking.')
            request.session.pop(SESSION_KEY, None)
            return redirect('select_show', movie_id=show.movie_id)

        if simulate_failure:
            messages.error(
                request,
                'Payment failed (demo simulation). No amount was charged - your seats have not been '
                'reserved. Please try again.',
            )
            return render(request, 'payment.html', {
                'show': show, 'movie': show.movie, 'seats': seats,
                'subtotal': subtotal, 'convenience_fee': convenience_fee, 'total': total,
                'payment_methods': Payment.PAYMENT_METHODS, 'selected_method': selected_method,
                'payment_failed': True,
            })

        if selected_method not in valid_methods:
            messages.error(request, 'Please choose a valid payment method.')
        else:
            try:
                booking = _create_booking(request.user, show, seats, total, selected_method)
            except SeatConflictError:
                messages.error(
                    request,
                    'Sorry, one or more selected seats were just booked by another customer. '
                    'Please select different seats.',
                )
                request.session.pop(SESSION_KEY, None)
                return redirect('select_seats', show_id=show.id)
            else:
                request.session.pop(SESSION_KEY, None)
                messages.success(request, 'Booking confirmed successfully!')
                return redirect('booking_success', booking_id=booking.booking_id)

    return render(request, 'payment.html', {
        'show': show,
        'movie': show.movie,
        'seats': seats,
        'subtotal': subtotal,
        'convenience_fee': convenience_fee,
        'total': total,
        'payment_methods': Payment.PAYMENT_METHODS,
        'selected_method': selected_method,
        'payment_failed': False,
    })


class SeatConflictError(Exception):
    """Raised when a seat gets booked by someone else between validation and commit."""


def _create_booking(user, show, seats, total, method):
    """Atomically create Booking + BookedSeat rows + Payment. Prevents double booking."""
    try:
        with transaction.atomic():
            # Re-check inside the transaction for the tightest possible window.
            conflict = BookedSeat.objects.select_for_update().filter(
                show=show, seat__in=seats, is_cancelled=False
            ).exists()
            if conflict:
                raise SeatConflictError()

            booking = Booking.objects.create(
                user=user,
                show=show,
                total_amount=total,
                status='CONFIRMED',
            )

            BookedSeat.objects.bulk_create([
                BookedSeat(booking=booking, show=show, seat=seat, price=seat.price)
                for seat in seats
            ])

            payment_status = 'PENDING' if method == 'CASH' else 'SUCCESS'
            Payment.objects.create(
                booking=booking,
                amount=total,
                status=payment_status,
                payment_method=method,
            )

            return booking
    except IntegrityError as exc:
        raise SeatConflictError() from exc



# Post-booking views


@login_required
def booking_success(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('show', 'show__movie', 'show__screen', 'show__screen__theatre', 'payment'),
        booking_id=booking_id,
        user=request.user,
    )
    booked_seats = booking.booked_seats.select_related('seat').order_by('seat__seat_number')

    return render(request, 'booking_success.html', {
        'booking': booking,
        'booked_seats': booked_seats,
    })


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related(
        'show', 'show__movie', 'show__screen', 'show__screen__theatre', 'payment'
    ).order_by('-booking_date')

    return render(request, 'my_bookings.html', {'bookings': bookings})


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('show', 'show__movie', 'show__screen', 'show__screen__theatre', 'payment'),
        booking_id=booking_id,
        user=request.user,
    )
    booked_seats = booking.booked_seats.select_related('seat').order_by('seat__seat_number')

    from django.conf import settings
    cutoff = booking.show.start_datetime - timezone.timedelta(minutes=settings.CANCELLATION_CUTOFF_MINUTES)
    can_cancel = booking.status == 'CONFIRMED' and timezone.now() < cutoff

    return render(request, 'booking_detail.html', {
        'booking': booking,
        'booked_seats': booked_seats,
        'can_cancel': can_cancel,
    })


@login_required
@require_POST
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)

    from django.conf import settings
    cutoff = booking.show.start_datetime - timezone.timedelta(minutes=settings.CANCELLATION_CUTOFF_MINUTES)

    if booking.status != 'CONFIRMED':
        messages.error(request, 'Only confirmed bookings can be cancelled.')
    elif timezone.now() >= cutoff:
        messages.error(request, 'This booking can no longer be cancelled (too close to show time).')
    else:
        with transaction.atomic():
            booking.status = 'CANCELLED'
            booking.save(update_fields=['status'])
            booking.booked_seats.update(is_cancelled=True)
        messages.success(request, 'Booking cancelled successfully. The seats are now available again.')

    return redirect('booking_detail', booking_id=booking.booking_id)



# Profile


@login_required
def profile(request):
    errors = {}
    values = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
    }

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        values = {'first_name': first_name, 'last_name': last_name, 'email': email}

        if email:
            try:
                validate_email(email)
            except ValidationError:
                errors.setdefault('email', []).append('Enter a valid email address.')
            else:
                if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
                    errors.setdefault('email', []).append('An account with this email already exists.')

        if not errors:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.save(update_fields=['first_name', 'last_name', 'email'])
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')

    bookings = Booking.objects.filter(user=request.user)
    upcoming_bookings = bookings.filter(
        status='CONFIRMED', show__show_date__gte=timezone.localdate()
    ).count()

    return render(request, 'profile.html', {
        'errors': errors,
        'values': values,
        'total_bookings': bookings.count(),
        'upcoming_bookings': upcoming_bookings,
    })



# Error handlers


def error_404(request, exception=None):
    return render(request, '404.html', status=404)


def error_403(request, exception=None):
    return render(request, '403.html', status=403)


def error_500(request):
    return render(request, '500.html', status=500)
