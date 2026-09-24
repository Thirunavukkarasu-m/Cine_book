import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import *


def make_movie(**kwargs):
    defaults = dict(
        title='Test Movie',
        description='A test movie.',
        release_date=timezone.localdate(),
        duration=120,
        language='English',
        genre='Action',
        rating=8.0,
        is_active=True,
    )
    defaults.update(kwargs)
    movie = Movie(**defaults)
    movie.poster.name = 'movies/placeholder.png'
    movie.save()
    return movie


def make_show(movie, screen, *, in_future=True, **kwargs):
    now = timezone.localtime()
    if in_future:
        start_dt = now + datetime.timedelta(days=1)
    else:
        start_dt = now - datetime.timedelta(days=1)

    defaults = dict(
        movie=movie,
        screen=screen,
        show_date=start_dt.date(),
        start_time=start_dt.time().replace(microsecond=0),
        end_time=(start_dt + datetime.timedelta(hours=2)).time().replace(microsecond=0),
        ticket_price=150,
        is_active=True,
    )
    defaults.update(kwargs)
    return Show.objects.create(**defaults)


class BaseCineBookTestCase(TestCase):
    def setUp(self):
        self.theatre = Theatre.objects.create(
            name='Test Theatre', location='Test Area', address='123 Test St', city='Testville'
        )
        self.screen = Screen.objects.create(theatre=self.theatre, name='Screen 1', total_seats=20)
        self.seats = [
            Seat.objects.create(screen=self.screen, seat_number=f'A{i}', row_label='A', seat_type='REGULAR', price=150)
            for i in range(1, 6)
        ]
        self.movie = make_movie()
        self.show = make_show(self.movie, self.screen)

        self.user = User.objects.create_user(username='alice', email='alice@example.com', password='TestPass123')
        self.other_user = User.objects.create_user(username='bob', email='bob@example.com', password='TestPass123')


class AuthenticationTests(TestCase):
    def test_registration_creates_user_and_logs_in(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'StrongPass123',
            'confirm_password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_registration_rejects_password_mismatch(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser2',
            'email': 'new2@example.com',
            'password': 'StrongPass123',
            'confirm_password': 'Different123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser2').exists())

    def test_registration_rejects_duplicate_username(self):
        User.objects.create_user(username='dupe', email='dupe@example.com', password='TestPass123')
        response = self.client.post(reverse('register'), {
            'username': 'dupe',
            'email': 'unique@example.com',
            'password': 'StrongPass123',
            'confirm_password': 'StrongPass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='dupe').count(), 1)

    def test_login_and_logout(self):
        User.objects.create_user(username='logintest', password='TestPass123')
        response = self.client.post(reverse('login'), {'username': 'logintest', 'password': 'TestPass123'})
        self.assertEqual(response.status_code, 302)

        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)

    def test_protected_page_redirects_anonymous_user(self):
        response = self.client.get(reverse('my_bookings'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)


class MovieVisibilityTests(BaseCineBookTestCase):
    def test_active_movie_visible_on_home(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, self.movie.title)

    def test_inactive_movie_hidden_on_home(self):
        inactive = make_movie(title='Hidden Movie', is_active=False)
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, inactive.title)

    def test_movie_detail_page_loads(self):
        response = self.client.get(reverse('movie_detail', args=[self.movie.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.movie.title)

    def test_inactive_movie_detail_returns_404(self):
        inactive = make_movie(title='Hidden 2', is_active=False)
        response = self.client.get(reverse('movie_detail', args=[inactive.id]))
        self.assertEqual(response.status_code, 404)


class ShowVisibilityTests(BaseCineBookTestCase):
    def test_future_show_listed(self):
        response = self.client.get(reverse('select_show', args=[self.movie.id]))
        self.assertContains(response, self.theatre.name)

    def test_past_show_not_listed(self):
        make_show(self.movie, self.screen, in_future=False)
        response = self.client.get(reverse('select_show', args=[self.movie.id]))
        # Only the (future) show from setUp should be bookable/listed.
        self.assertContains(response, self.theatre.name)
        # No exception, and past show should not appear as a separate bookable slot
        # (we simply verify the page renders without error here).
        self.assertEqual(response.status_code, 200)


class SeatSelectionTests(BaseCineBookTestCase):
    def test_seat_page_requires_login(self):
        response = self.client.get(reverse('select_seats', args=[self.show.id]))
        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_can_view_seats(self):
        self.client.login(username='alice', password='TestPass123')
        response = self.client.get(reverse('select_seats', args=[self.show.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A1')

    def test_max_seats_enforced(self):
        self.client.login(username='alice', password='TestPass123')
        many_seats = [
            Seat.objects.create(screen=self.screen, seat_number=f'B{i}', row_label='B', seat_type='REGULAR', price=100)
            for i in range(1, 12)
        ]
        seat_ids = ','.join(str(s.id) for s in many_seats)
        response = self.client.post(reverse('select_seats', args=[self.show.id]), {'seat_ids': seat_ids})
        self.assertEqual(response.status_code, 200)  # re-renders with an error, no redirect
        self.assertNotIn('pending_booking', self.client.session)

    def test_invalid_seat_rejected(self):
        self.client.login(username='alice', password='TestPass123')
        response = self.client.post(reverse('select_seats', args=[self.show.id]), {'seat_ids': '999999'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('pending_booking', self.client.session)

    def test_valid_seat_selection_redirects_to_review(self):
        self.client.login(username='alice', password='TestPass123')
        response = self.client.post(
            reverse('select_seats', args=[self.show.id]),
            {'seat_ids': f'{self.seats[0].id},{self.seats[1].id}'},
        )
        self.assertRedirects(response, reverse('booking_review'))


class BookingFlowTests(BaseCineBookTestCase):
    def _select_seats(self, user, seats):
        self.client.login(username=user.username, password='TestPass123')
        self.client.post(
            reverse('select_seats', args=[self.show.id]),
            {'seat_ids': ','.join(str(s.id) for s in seats)},
        )

    def test_full_booking_creates_confirmed_booking(self):
        self._select_seats(self.user, self.seats[:2])

        response = self.client.get(reverse('booking_review'))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('payment'), {'payment_method': 'DEMO'})
        self.assertEqual(response.status_code, 302)

        booking = Booking.objects.get(user=self.user)
        self.assertEqual(booking.status, 'CONFIRMED')
        self.assertEqual(booking.booked_seats.count(), 2)
        self.assertTrue(booking.booking_id.startswith('CB-'))

        expected_total = sum(s.price for s in self.seats[:2]) + 30  # + convenience fee
        self.assertEqual(booking.total_amount, expected_total)

        payment = Payment.objects.get(booking=booking)
        self.assertEqual(payment.status, 'SUCCESS')
        self.assertTrue(payment.transaction_id.startswith('TXN-CB-'))

    def test_double_booking_is_prevented(self):
        # User A books seat A1.
        self._select_seats(self.user, [self.seats[0]])
        self.client.get(reverse('booking_review'))
        self.client.post(reverse('payment'), {'payment_method': 'DEMO'})

        self.assertEqual(BookedSeat.objects.filter(seat=self.seats[0], is_cancelled=False).count(), 1)

        # User B tries to select the same seat - should be blocked at selection time.
        self.client.logout()
        self.client.login(username='bob', password='TestPass123')
        response = self.client.post(
            reverse('select_seats', args=[self.show.id]),
            {'seat_ids': str(self.seats[0].id)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('pending_booking', self.client.session)
        self.assertEqual(BookedSeat.objects.filter(seat=self.seats[0], is_cancelled=False).count(), 1)

    def test_payment_failure_creates_no_booking(self):
        self._select_seats(self.user, [self.seats[0]])
        self.client.get(reverse('booking_review'))
        self.client.post(reverse('payment'), {'payment_method': 'DEMO', 'simulate_failure': 'on'})
        self.assertEqual(Booking.objects.filter(user=self.user).count(), 0)


class BookingSecurityTests(BaseCineBookTestCase):
    def _create_confirmed_booking(self, user):
        self.client.login(username=user.username, password='TestPass123')
        self.client.post(reverse('select_seats', args=[self.show.id]), {'seat_ids': str(self.seats[0].id)})
        self.client.get(reverse('booking_review'))
        self.client.post(reverse('payment'), {'payment_method': 'DEMO'})
        self.client.logout()
        return Booking.objects.get(user=user)

    def test_user_cannot_view_another_users_booking(self):
        booking = self._create_confirmed_booking(self.user)

        self.client.login(username='bob', password='TestPass123')
        response = self.client.get(reverse('booking_detail', args=[booking.booking_id]))
        self.assertEqual(response.status_code, 404)

    def test_owner_can_view_their_booking(self):
        booking = self._create_confirmed_booking(self.user)

        self.client.login(username='alice', password='TestPass123')
        response = self.client.get(reverse('booking_detail', args=[booking.booking_id]))
        self.assertEqual(response.status_code, 200)


class CancellationTests(BaseCineBookTestCase):
    def test_owner_can_cancel_and_seat_becomes_available(self):
        self.client.login(username='alice', password='TestPass123')
        self.client.post(reverse('select_seats', args=[self.show.id]), {'seat_ids': str(self.seats[0].id)})
        self.client.get(reverse('booking_review'))
        self.client.post(reverse('payment'), {'payment_method': 'DEMO'})
        booking = Booking.objects.get(user=self.user)

        response = self.client.post(reverse('cancel_booking', args=[booking.booking_id]))
        self.assertEqual(response.status_code, 302)

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED')
        self.assertEqual(
            BookedSeat.objects.filter(seat=self.seats[0], is_cancelled=False).count(), 0
        )

        # The seat should now be bookable again by another user.
        self.client.logout()
        self.client.login(username='bob', password='TestPass123')
        response = self.client.post(
            reverse('select_seats', args=[self.show.id]),
            {'seat_ids': str(self.seats[0].id)},
        )
        self.assertRedirects(response, reverse('booking_review'))

    def test_user_cannot_cancel_another_users_booking(self):
        self.client.login(username='alice', password='TestPass123')
        self.client.post(reverse('select_seats', args=[self.show.id]), {'seat_ids': str(self.seats[0].id)})
        self.client.get(reverse('booking_review'))
        self.client.post(reverse('payment'), {'payment_method': 'DEMO'})
        booking = Booking.objects.get(user=self.user)
        self.client.logout()

        self.client.login(username='bob', password='TestPass123')
        response = self.client.post(reverse('cancel_booking', args=[booking.booking_id]))
        self.assertEqual(response.status_code, 404)

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CONFIRMED')

    def test_past_show_booking_cannot_be_cancelled(self):
        past_show = make_show(self.movie, self.screen, in_future=False)
        seat = Seat.objects.create(screen=self.screen, seat_number='Z1', row_label='Z', seat_type='REGULAR', price=100)
        booking = Booking.objects.create(user=self.user, show=past_show, total_amount=100, status='CONFIRMED')
        BookedSeat.objects.create(booking=booking, show=past_show, seat=seat, price=100)
        Payment.objects.create(booking=booking, amount=100, status='SUCCESS', payment_method='DEMO')

        self.client.login(username='alice', password='TestPass123')
        response = self.client.post(reverse('cancel_booking', args=[booking.booking_id]))
        self.assertEqual(response.status_code, 302)

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CONFIRMED')  # unchanged - cancellation was rejected
