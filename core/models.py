import uuid

from django.db import models
from authentication.models import *


class Venue(models.Model):
    venue_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue_name = models.CharField(max_length=100)
    capacity = models.IntegerField(default=1)
    address = models.TextField()
    city = models.CharField(max_length=100)
    SEATING_CHOICES = [
        ("Free Seating", "Free Seating"),
        ("Reserved Seating", "Reserved Seating"),
    ]
    jenis_seating = models.CharField(max_length=20, choices=SEATING_CHOICES)

    class Meta:
        managed = False
        db_table = "venue"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacity__gt=0), name="capacity_check"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    jenis_seating__in=["Free Seating", "Reserved Seating"]
                ),
                name="jenis_seating_check",
            ),
        ]


class Seat(models.Model):
    seat_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.CharField(max_length=50)
    seat_number = models.CharField(max_length=10)
    row_number = models.CharField(max_length=10)
    venue = models.ForeignKey(Venue, models.CASCADE, db_column="venue_id")

    class Meta:
        managed = False
        db_table = "seat"


class Event(models.Model):
    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_datetime = models.DateTimeField()
    event_title = models.CharField(max_length=200)
    venue = models.ForeignKey(Venue, models.RESTRICT, db_column="venue_id")
    organizer = models.ForeignKey(Organizer, models.RESTRICT, db_column="organizer_id")

    class Meta:
        managed = False
        db_table = "event"


class Artist(models.Model):
    artist_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    genre = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "artist"


class EventArtist(models.Model):
    event = models.ForeignKey(Event, models.CASCADE, db_column="event_id")
    artist = models.ForeignKey(Artist, models.RESTRICT, db_column="artist_id")
    role = models.CharField(max_length=100, blank=True, null=True)
    pk = models.CompositePrimaryKey("event", "artist")

    class Meta:
        managed = False
        db_table = "event_artist"


class TicketCategory(models.Model):
    category_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category_name = models.CharField(max_length=50)
    quota = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tevent = models.ForeignKey(Event, models.CASCADE, db_column="tevent_id")

    class Meta:
        managed = False
        db_table = "ticket_category"
        constraints = [
            models.CheckConstraint(condition=models.Q(quota__gt=0), name="quota_check"),
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="price_check"
            ),
        ]


class Order(models.Model):
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_date = models.DateTimeField()
    payment_status = models.CharField(max_length=20)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    customer = models.ForeignKey(Customer, models.RESTRICT, db_column="customer_id")

    class Meta:
        managed = False
        db_table = "ORDER"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0), name="totalamount_check"
            ),
        ]


class Ticket(models.Model):
    ticket_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_code = models.CharField(unique=True, max_length=100)
    tcategory = models.ForeignKey(
        TicketCategory, models.RESTRICT, db_column="tcategory_id"
    )
    torder = models.ForeignKey(Order, models.RESTRICT, db_column="torder_id")
    status = models.CharField(max_length=20, default='VALID')  # TAMBAH INI

    class Meta:
        managed = False
        db_table = "ticket"


class HasRelationship(models.Model):
    seat = models.ForeignKey(Seat, models.RESTRICT, db_column="seat_id")
    ticket = models.ForeignKey(Ticket, models.CASCADE, db_column="ticket_id")
    pk = models.CompositePrimaryKey("seat", "ticket")

    class Meta:
        managed = False
        db_table = "has_relationship"


class Promotion(models.Model):
    promotion_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    promo_code = models.CharField(unique=True, max_length=50)
    discount_type = models.CharField(max_length=20, default="NOMINAL")
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    start_date = models.DateField()
    end_date = models.DateField()
    usage_limit = models.IntegerField(default=1)

    class Meta:
        managed = False
        db_table = "promotion"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(discount_type__in=["NOMINAL", "PERCENTAGE"]),
                name="discounttype_check",
            ),
            models.CheckConstraint(
                condition=models.Q(discount_value__gt=0), name="discountvalue_check"
            ),
            models.CheckConstraint(
                condition=models.Q(usage_limit__gt=0), name="usagelimit_check"
            ),
        ]


class OrderPromotion(models.Model):
    order_promotion_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    promotion = models.ForeignKey(Promotion, models.RESTRICT, db_column="promotion_id")
    order = models.ForeignKey(Order, models.CASCADE, db_column="order_id")

    class Meta:
        managed = False
        db_table = "order_promotion"
