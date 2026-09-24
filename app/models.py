import random
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone



# 1. MOVIE

class Movie(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    poster = models.ImageField(upload_to='movies/')
    release_date = models.DateField()
    duration = models.IntegerField(help_text='Duration in minutes')
    language = models.CharField(max_length=50)
    genre = models.CharField(max_length=100, default='Unknown')
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)

    trailer_url = models.URLField(blank=True, help_text='YouTube trailer link (optional)')
    certificate = models.CharField(
        max_length=10,
        blank=True,
        help_text='e.g. U, UA, A',
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'movie'
        verbose_name = 'Movie'
        verbose_name_plural = 'Movies'
        ordering = ['-release_date']



# 2. THEATRE

class Theatre(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'theatre'
        verbose_name = 'Theatre'
        verbose_name_plural = 'Theatres'
        ordering = ['name']



# 3. SCREEN

class Screen(models.Model):
    theatre = models.ForeignKey(Theatre, on_delete=models.CASCADE, related_name='screens')
    name = models.CharField(max_length=100)
    total_seats = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.theatre.name} - {self.name}'

    class Meta:
        db_table = 'screen'
        verbose_name = 'Screen'
        verbose_name_plural = 'Screens'
        ordering = ['theatre', 'name']
        constraints = [
            models.UniqueConstraint(fields=['theatre', 'name'], name='unique_screen_per_theatre'),
        ]



# 4. SEAT

class Seat(models.Model):
    SEAT_TYPES = [
        ('REGULAR', 'Regular'),
        ('PREMIUM', 'Premium'),
        ('RECLINER', 'Recliner'),
    ]

    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10, help_text='e.g. A1, B5')
    row_label = models.CharField(max_length=5, blank=True, help_text='e.g. A, B, C')

    seat_type = models.CharField(max_length=20, choices=SEAT_TYPES, default='REGULAR')
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Auto derive the row label from the seat number (A1 -> A) if not set.
        if not self.row_label and self.seat_number:
            self.row_label = ''.join(ch for ch in self.seat_number if ch.isalpha()) or self.seat_number[:1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.screen.name} - {self.seat_number}'

    class Meta:
        db_table = 'seat'
        verbose_name = 'Seat'
        verbose_name_plural = 'Seats'
        ordering = ['screen', 'row_label', 'seat_number']
        constraints = [
            models.UniqueConstraint(fields=['screen', 'seat_number'], name='unique_seat_per_screen'),
        ]



# 5. SHOW

class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='shows')
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name='shows')

    show_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    ticket_price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

    @property
    def start_datetime(self):
        """Timezone-aware datetime combining show_date and start_time."""
        naive = timezone.datetime.combine(self.show_date, self.start_time)
        return timezone.make_aware(naive, timezone.get_current_timezone())

    @property
    def is_past(self):
        return self.start_datetime < timezone.now()

    @property
    def is_bookable(self):
        return self.is_active and not self.is_past

    def __str__(self):
        return f'{self.movie.title} - {self.screen} - {self.show_date} - {self.start_time}'

    class Meta:
        db_table = 'show'
        verbose_name = 'Show'
        verbose_name_plural = 'Shows'
        ordering = ['show_date', 'start_time']
        constraints = [
            models.UniqueConstraint(
                fields=['screen', 'show_date', 'start_time'],
                name='unique_show_on_screen',
            )
        ]



# 6. BOOKING

def generate_booking_id():
    """Generate a human-friendly, unique booking ID like CB-20260914-AB123."""
    while True:
        stamp = timezone.now().strftime('%Y%m%d')
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        candidate = f'CB-{stamp}-{suffix}'
        if not Booking.objects.filter(booking_id=candidate).exists():
            return candidate


class Booking(models.Model):
    BOOKING_STATUS = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='bookings')

    booking_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='PENDING')
    booking_id = models.CharField(max_length=30, unique=True, default=generate_booking_id, editable=False)

    def __str__(self):
        return self.booking_id

    class Meta:
        db_table = 'booking'
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        ordering = ['-booking_date']



# 7. BOOKED SEAT

class BookedSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_seats')
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='booked_seats')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='booked_seats')
    price = models.DecimalField(max_digits=8, decimal_places=2)

    # Mirrors booking.status == 'CANCELLED'. Kept on this row (rather than only
    # on the related Booking) so PostgreSQL can enforce a *partial* unique
    # index: a seat can only be held by ONE active (non-cancelled) booking
    # per show, while still letting the seat be re-booked after a
    # cancellation and keeping full history of the old booking.
    is_cancelled = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.booking.booking_id} - {self.seat.seat_number}'

    class Meta:
        db_table = 'booked_seat'
        verbose_name = 'Booked Seat'
        verbose_name_plural = 'Booked Seats'
        constraints = [
            models.UniqueConstraint(
                fields=['show', 'seat'],
                condition=models.Q(is_cancelled=False),
                name='unique_active_seat_per_show',
            ),
        ]



# 8. PAYMENT

def generate_transaction_id():
    while True:
        suffix = ''.join(random.choices(string.digits, k=6))
        candidate = f'TXN-CB-{suffix}'
        if not Payment.objects.filter(transaction_id=candidate).exists():
            return candidate


class Payment(models.Model):
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    PAYMENT_METHODS = [
        ('UPI', 'UPI'),
        ('CARD', 'Credit / Debit Card'),
        ('CASH', 'Cash at Counter'),
        ('DEMO', 'Demo Payment'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, blank=True)
    transaction_id = models.CharField(max_length=100, unique=True, default=generate_transaction_id)
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.booking.booking_id

    class Meta:
        db_table = 'payment'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
