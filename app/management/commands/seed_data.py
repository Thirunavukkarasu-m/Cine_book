"""
Seed CineBook with a realistic demo dataset so the ENTIRE application can be
tested end-to-end immediately after installation:

    Home -> Movie -> Show -> Seat Selection -> Booking -> Demo Payment -> Ticket -> My Bookings

Usage:
    python manage.py seed_data

This command is SAFE TO RUN MULTIPLE TIMES. Every step uses get_or_create
(or an explicit "already exists" check), so re-running it will never create
duplicate movies, theatres, screens, seats, shows, users or bookings.

Data is created in dependency order:
    Movies -> Theatres -> Screens -> Seats -> Shows -> Demo users -> Sample bookings
"""
import datetime
import io

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app.models import Booking, BookedSeat, Movie, Payment, Screen, Seat, Show, Theatre

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Demo dataset — edit these lists to change what gets seeded.
# ---------------------------------------------------------------------------


MOVIES = [
    dict(
        title='Mahaan',
        description='A gripping Tamil crime drama about family, loyalty and ambition.',
        release_date_offset=-30,
        duration=155,
        language='Tamil',
        genre='Drama',
        rating=7.8,
        certificate='UA',
        poster_color=(220, 38, 38),
        poster_path='movies/mahaan-poster-1643882959.jpg',
    ),

    dict(
        title='Vikram',
        description='A Tamil action thriller following a special agent uncovering a dangerous criminal network.',
        release_date_offset=-25,
        duration=174,
        language='Tamil',
        genre='Action',
        rating=8.3,
        certificate='UA',
       
        poster_path='movies/Dhruva-Natchathiram-4.jpg',
    ),

    dict(
        title='Jailer',
        description='A retired jailer is forced to confront a dangerous criminal gang to protect his family.',
        release_date_offset=-20,
        duration=168,
        language='Tamil',
        genre='Action',
        rating=7.5,
        certificate='UA',
        poster_color=(30, 41, 59),
    ),

    dict(
        title='Leo',
        description='A quiet cafe owner is pulled into a violent past when dangerous men arrive looking for him.',
        release_date_offset=-15,
        duration=164,
        language='Tamil',
        genre='Action',
        rating=7.4,
        certificate='UA',
        poster_color=(180, 83, 9),
    ),

    dict(
        title='Soorarai Pottru',
        description='An ambitious man dreams of making air travel affordable for ordinary people.',
        release_date_offset=-10,
        duration=153,
        language='Tamil',
        genre='Drama',
        rating=8.1,
        certificate='U',
        poster_color=(5, 150, 105),
    ),

    dict(
        title='96',
        description='Two school sweethearts meet years later and revisit their unforgettable memories.',
        release_date_offset=-8,
        duration=158,
        language='Tamil',
        genre='Romance',
        rating=8.5,
        certificate='U',
        poster_color=(190, 24, 93),
    ),

    dict(
        title='Doctor',
        description='A calm and intelligent doctor gets involved in a dangerous kidnapping case.',
        release_date_offset=-5,
        duration=148,
        language='Tamil',
        genre='Comedy',
        rating=7.4,
        certificate='UA',
        poster_color=(109, 40, 217),
    ),

    dict(
        title='Master',
        description='An alcoholic professor takes on a powerful gangster running a juvenile home.',
        release_date_offset=-3,
        duration=179,
        language='Tamil',
        genre='Action',
        rating=7.3,
        certificate='UA',
        poster_color=(37, 99, 235),
    ),

    dict(
        title='Kaithi',
        description='A prisoner gets one night to reunite with his daughter while helping police stop a drug gang.',
        release_date_offset=-2,
        duration=145,
        language='Tamil',
        genre='Thriller',
        rating=8.4,
        certificate='UA',
        poster_color=(15, 23, 42),
    ),

    dict(
        title='Kadaisi Vivasayi',
        description='A simple farmer becomes the centre of an unexpected legal and emotional journey.',
        release_date_offset=-1,
        duration=145,
        language='Tamil',
        genre='Drama',
        rating=8.0,
        certificate='U',
        poster_color=(22, 101, 52),
    ),
]


THEATRES = [
    dict(
        name='PVR Ampa Skywalk', location='Aminjikarai',
        address='Ambit IT Park, Ampa Skywalk Mall, Aminjikarai, Chennai - 600029',
        city='Chennai', screen_count=3,
    ),
    dict(
        name='INOX Citi Centre', location='Mylapore',
        address='Citi Centre Mall, 10 Dr Radhakrishnan Salai, Mylapore, Chennai - 600004',
        city='Chennai', screen_count=2,
    ),
    dict(
        name='AGS Cinemas Villivakkam', location='Villivakkam',
        address='142 GST Road, Villivakkam, Chennai - 600049',
        city='Chennai', screen_count=2,
    ),
    dict(
        name='Sathyam Cinemas', location='Royapettah',
        address='8 Thiyagaraya Street, Royapettah, Chennai - 600014',
        city='Chennai', screen_count=3,
    ),
    dict(
        name='Luxe Cinemas Vadapalani', location='Vadapalani',
        address='Forum Vijaya Mall, Arcot Road, Vadapalani, Chennai - 600026',
        city='Chennai', screen_count=2,
    ),
]

# Seat layout used for every screen: 8 rows (A-H) x 10 seats.
# Front rows are Regular, middle rows Premium, back rows Recliner - like a real cinema.
SEAT_ROW_TYPES = [
    ('A', 'REGULAR'), ('B', 'REGULAR'), ('C', 'REGULAR'),
    ('D', 'PREMIUM'), ('E', 'PREMIUM'), ('F', 'PREMIUM'),
    ('G', 'RECLINER'), ('H', 'RECLINER'),
]
SEATS_PER_ROW = 10
SEAT_PRICES = {'REGULAR': 150, 'PREMIUM': 220, 'RECLINER': 350}

# Show timings used when scheduling (kept a little apart so two movies never
# clash on the same screen on the same day).
MOVIE_SLOT_A_TIMES = [datetime.time(10, 0), datetime.time(17, 0)]
MOVIE_SLOT_B_TIMES = [datetime.time(13, 30), datetime.time(20, 30)]
SHOW_DAYS_AHEAD = 4  # today + the next 3 days

DEMO_USERS = [
    dict(username='demo_user', email='demo_user@example.com', password='DemoPass123'),
    dict(username='priya_sharma', email='priya.sharma@example.com', password='DemoPass123'),
]


class Command(BaseCommand):
    help = 'Seed CineBook with a realistic Chennai movie/theatre/show demo dataset.'

    def handle(self, *args, **options):
        with transaction.atomic():
            movies = self._seed_movies()
            theatres = self._seed_theatres()
            screens = self._seed_screens(theatres)
            self._seed_seats(screens)
            shows_created = self._seed_shows(movies, screens)
            users = self._seed_demo_users()
            self._seed_sample_bookings(users, shows_created)

        self._print_summary()

    # ------------------------------------------------------------------
    # 1. MOVIES
    # ------------------------------------------------------------------
    def _seed_movies(self):
        created_movies = []
        for data in MOVIES:
            defaults = dict(
                description=data['description'],
                release_date=timezone.localdate() + datetime.timedelta(days=data['release_date_offset']),
                duration=data['duration'],
                language=data['language'],
                genre=data['genre'],
                rating=data['rating'],
                certificate=data['certificate'],
                is_active=True,
            )
            movie, created = Movie.objects.get_or_create(title=data['title'], defaults=defaults)

            if created and not movie.poster:
                poster_path = data.get('poster_path')
                if poster_path:
                    # Re-use a real poster image already shipped with the project.
                    movie.poster.name = poster_path
                    movie.save(update_fields=['poster'])
                else:
                    self._attach_generated_poster(movie, data['title'], data['poster_color'])

            created_movies.append(movie)
        return created_movies

    def _attach_generated_poster(self, movie, title, color):
        """Generate a simple, distinct placeholder poster with the movie title on it."""
        filename = f"{title.replace(' ', '_').lower()}_poster.png"

        if not PIL_AVAILABLE:
            # Fallback: a tiny solid-colour PNG if Pillow somehow isn't available.
            tiny_png = bytes.fromhex(
                '89504e470d0a1a0a0000000d4948445200000001000000010806000000'
                '1f15c4890000000a49444154789c6360000002000100ffff03000006000557'
                'bfabd40000000049454e44ae426082'
            )
            movie.poster.save(filename, ContentFile(tiny_png), save=True)
            return

        width, height = 300, 450
        image = Image.new('RGB', (width, height), color)
        draw = ImageDraw.Draw(image)

        # Subtle gradient band at the bottom for a "poster" feel.
        for y in range(height - 140, height):
            shade = int(20 * (y - (height - 140)) / 140)
            draw.line([(0, y), (width, y)], fill=tuple(max(c - shade, 0) for c in color))

        font = ImageFont.load_default()
        words = title.split()
        lines, current = [], ''
        for word in words:
            trial = f'{current} {word}'.strip()
            if len(trial) > 16:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)

        y = height - 120
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            draw.text(((width - text_w) / 2, y), line, fill='white', font=font)
            y += 20

        draw.text((14, 14), 'CINEBOOK', fill='white', font=font)

        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        movie.poster.save(filename, ContentFile(buffer.getvalue()), save=True)

    # ------------------------------------------------------------------
    # 2. THEATRES
    # ------------------------------------------------------------------
    def _seed_theatres(self):
        theatres = []
        for data in THEATRES:
            theatre, _ = Theatre.objects.get_or_create(
                name=data['name'],
                defaults=dict(
                    location=data['location'],
                    address=data['address'],
                    city=data['city'],
                    is_active=True,
                ),
            )
            theatres.append(theatre)
        return theatres

    # ------------------------------------------------------------------
    # 3. SCREENS
    # ------------------------------------------------------------------
    def _seed_screens(self, theatres):
        screens = []
        total_seats = len(SEAT_ROW_TYPES) * SEATS_PER_ROW

        for theatre_data, theatre in zip(THEATRES, theatres):
            for screen_number in range(1, theatre_data['screen_count'] + 1):
                screen, _ = Screen.objects.get_or_create(
                    theatre=theatre,
                    name=f'Screen {screen_number}',
                    defaults={'total_seats': total_seats},
                )
                screens.append(screen)
        return screens

    # ------------------------------------------------------------------
    # 4. SEATS
    # ------------------------------------------------------------------
    def _seed_seats(self, screens):
        for screen in screens:
            if screen.seats.exists():
                continue  # already generated for this screen - do not duplicate

            seats_to_create = []
            for row_label, seat_type in SEAT_ROW_TYPES:
                for number in range(1, SEATS_PER_ROW + 1):
                    seats_to_create.append(
                        Seat(
                            screen=screen,
                            seat_number=f'{row_label}{number}',
                            row_label=row_label,
                            seat_type=seat_type,
                            price=SEAT_PRICES[seat_type],
                        )
                    )
            Seat.objects.bulk_create(seats_to_create)

    # ------------------------------------------------------------------
    # 5. SHOWS
    # ------------------------------------------------------------------
    def _seed_shows(self, movies, screens):
        """
        Every screen gets 2 movies (rotating through the full movie list so
        different theatres show different films), each playing at its own
        fixed set of times across the next few days - so no two shows ever
        clash on the same screen.
        """
        today = timezone.localdate()
        created_shows = []

        for screen_index, screen in enumerate(screens):
            movie_a = movies[(screen_index * 2) % len(movies)]
            movie_b = movies[(screen_index * 2 + 1) % len(movies)]

            for day_offset in range(SHOW_DAYS_AHEAD):
                show_date = today + datetime.timedelta(days=day_offset)

                for movie, times in ((movie_a, MOVIE_SLOT_A_TIMES), (movie_b, MOVIE_SLOT_B_TIMES)):
                    for start_time in times:
                        end_dt = (
                            datetime.datetime.combine(show_date, start_time)
                            + datetime.timedelta(minutes=movie.duration + 15)  # +15 min interval/ads
                        )
                        show, _ = Show.objects.get_or_create(
                            screen=screen,
                            show_date=show_date,
                            start_time=start_time,
                            defaults=dict(
                                movie=movie,
                                end_time=end_dt.time(),
                                ticket_price=SEAT_PRICES['REGULAR'],
                                is_active=True,
                            ),
                        )
                        created_shows.append(show)

        return created_shows

    # ------------------------------------------------------------------
    # 6. DEMO USERS
    # ------------------------------------------------------------------
    def _seed_demo_users(self):
        users = []
        for data in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={'email': data['email']},
            )
            if created:
                user.set_password(data['password'])
                user.save()
            users.append(user)
        return users

    # ------------------------------------------------------------------
    # 7. SAMPLE BOOKINGS (kept minimal on purpose - most seats stay free
    #    so you can test the full booking flow yourself).
    # ------------------------------------------------------------------
    def _seed_sample_bookings(self, users, shows):
        if not shows or len(users) < 2:
            return

        future_shows = sorted(
            (s for s in shows if s.is_bookable),
            key=lambda s: (s.show_date, s.start_time),
        )
        if not future_shows:
            return

        demo_user, second_user = users[0], users[1]

        # One small booking for demo_user - 2 Regular seats.
        self._create_sample_booking(demo_user, future_shows[0], ['A1', 'A2'])

        # One small booking for the second demo user, on a different show.
        if len(future_shows) > 1:
            self._create_sample_booking(second_user, future_shows[1], ['D3'])

    def _create_sample_booking(self, user, show, seat_numbers):
        if Booking.objects.filter(user=user, show=show).exists():
            return  # already seeded - keep the command idempotent

        seats = list(Seat.objects.filter(screen=show.screen, seat_number__in=seat_numbers))
        if not seats:
            return

        already_taken = BookedSeat.objects.filter(show=show, seat__in=seats, is_cancelled=False).exists()
        if already_taken:
            return

        total = sum(seat.price for seat in seats) + 30  # + demo convenience fee

        booking = Booking.objects.create(user=user, show=show, total_amount=total, status='CONFIRMED')
        BookedSeat.objects.bulk_create([
            BookedSeat(booking=booking, show=show, seat=seat, price=seat.price) for seat in seats
        ])
        Payment.objects.create(booking=booking, amount=total, status='SUCCESS', payment_method='DEMO')

    # ------------------------------------------------------------------
    def _print_summary(self):
        self.stdout.write(self.style.SUCCESS('\nCineBook demo data is ready!\n'))
        self.stdout.write(f'  Movies    : {Movie.objects.count()}')
        self.stdout.write(f'  Theatres  : {Theatre.objects.count()} (Chennai)')
        self.stdout.write(f'  Screens   : {Screen.objects.count()}')
        self.stdout.write(f'  Seats     : {Seat.objects.count()}')
        self.stdout.write(f'  Shows     : {Show.objects.count()}')
        self.stdout.write(f'  Bookings  : {Booking.objects.count()}\n')

        self.stdout.write('Demo login accounts (for testing the booking flow):')
        for data in DEMO_USERS:
            self.stdout.write(f"  username: {data['username']:<14} password: {data['password']}")

        self.stdout.write(
            '\nNo admin/superuser account is created by this command. '
            'Run "python manage.py createsuperuser" to create your own admin login.'
        )
        self.stdout.write(
            '\nYou can now test the full flow: Home -> Movie -> Show -> Seat Selection '
            '-> Booking -> Demo Payment -> Ticket -> My Bookings.'
        )
