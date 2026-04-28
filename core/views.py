from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from django.db import IntegrityError
import uuid, json

from .models import (
    Venue,
    Seat,
    HasRelationship,
    Event,
    Ticket,
    TicketCategory,
    Order,
    Promotion,
)
from authentication.models import UserAccount, AccountRole, Customer, Organizer


def home_view(request):
    return redirect("dashboard")


def artist_list_view(request):
    return render(request, "artist/artist.html")


def ticket_category_list_view(request):
    return render(request, "ticket/ticket-category.html")


def get_role(user_id):
    if not user_id:
        return "guest"
    try:
        account_role = AccountRole.objects.select_related("role").get(user_id=user_id)
        return account_role.role.role_name.lower()
    except AccountRole.DoesNotExist:
        return "guest"


def dashboard_pengguna(request, page="main"):
    user_id = request.session.get("user_id")

    # ======================== USER GUEST ========================
    if not user_id:
        trending_events_qs = Event.objects.select_related("venue").all()[:3]
        trending_events = [
            (e.event_title, e.event_datetime, e.venue.venue_name)
            for e in trending_events_qs
        ]

        context = {
            "username": "Guest",
            "nama": "Pengunjung Baru",
            "is_guest": True,
            "page": page,
            "trending_events": trending_events,
        }

        if page == "profile":
            context.update(
                {
                    "nama_lengkap": "Pengunjung Baru",
                    "nomor_telepon": "-",
                    "role_display": "Guest",
                }
            )
            return render(request, "dashboard/profile.html", context)

        return render(request, "dashboard/customer.html", context)

    # ======================== USER LOGIN ========================
    user = get_object_or_404(UserAccount, user_id=user_id)

    customer = Customer.objects.filter(user=user).first()
    organizer = Organizer.objects.filter(user=user).first()

    if request.method == "POST" and page == "profile":
        nama_baru = request.POST.get("nama_lengkap")
        telp_baru = request.POST.get("nomor_telepon")

        if customer:
            Customer.objects.filter(user=user).update(
                full_name=nama_baru, phone_number=telp_baru
            )
        elif organizer:
            Organizer.objects.filter(user=user).update(organizer_name=nama_baru)

        messages.success(request, "Profil Anda berhasil diperbarui!")
        return redirect("dashboard_page", page="profile")

    username = user.username
    full_name = customer.full_name if customer else None
    phone_number = customer.phone_number if customer else None
    organizer_name = organizer.organizer_name if organizer else None

    raw_role_name = get_role(user_id)

    if raw_role_name == "administrator":
        role_display = "admin"
    elif raw_role_name == "organizer":
        role_display = "organizer"
    else:
        role_display = "customer"

    context = {
        "username": username,
        "user_id": user_id,
        "is_guest": False,
        "page": page,
        "role": role_display,
    }

    if page == "profile":
        display_name = (
            organizer_name if role_display == "organizer" else (full_name or username)
        )
        context.update(
            {
                "nama_lengkap": display_name,
                "nomor_telepon": phone_number or "-",
                "role_display": raw_role_name.capitalize(),
            }
        )
        return render(request, "dashboard/profile.html", context)

    if role_display == "customer":
        if customer:
            tiket_aktif = Ticket.objects.filter(
                torder__customer=customer,
                tcategory__tevent__event_datetime__gte=timezone.now(),
            ).count()

            # PERBAIKAN: Gunakan 'order_id' bukan 'id'
            total_acara = (
                Order.objects.filter(customer=customer)
                .values("order_id")
                .distinct()
                .count()
            )
            kode_promo = Promotion.objects.filter(end_date__gte=timezone.now()).count()

            total_amount_dict = Order.objects.filter(customer=customer).aggregate(
                Sum("total_amount")
            )
            belanja = total_amount_dict["total_amount__sum"] or 0.0

            belanja_display = (
                f"Rp {belanja / 1000000:.1f}M"
                if belanja >= 1000000
                else f"Rp {int(belanja/1000)}K"
            )

            tiket_list_qs = (
                Ticket.objects.filter(
                    torder__customer=customer,
                    tcategory__tevent__event_datetime__gte=timezone.now(),
                )
                .select_related("tcategory__tevent__venue")
                .order_by("tcategory__tevent__event_datetime")[:2]
            )

            tiket_list = [
                (
                    t.tcategory.tevent.event_title,
                    t.tcategory.tevent.event_datetime,
                    t.tcategory.tevent.venue.venue_name,
                    t.tcategory.category_name,
                )
                for t in tiket_list_qs
            ]

            context.update(
                {
                    "nama": full_name or username,
                    "tiket_aktif": tiket_aktif,
                    "total_acara": total_acara,
                    "kode_promo": kode_promo,
                    "total_belanja": belanja_display,
                    "tiket_list": tiket_list,
                }
            )

    elif role_display == "admin":
        context.update({"nama": "System Console"})

    else:
        if organizer:
            count_event = Event.objects.filter(organizer=organizer).count()
            context.update(
                {"nama": organizer_name or username, "count_event": count_event}
            )

    return render(request, f"dashboard/{role_display}.html", context)


def ticket_list(request):
    user_id = request.session.get("user_id")
    role = get_role(user_id)
    user_display_name = "Guest"

    if user_id:
        if role == "customer":
            cust = Customer.objects.filter(user_id=user_id).first()
            user_display_name = cust.full_name if cust else "Pelanggan"
        elif role == "organizer":
            org = Organizer.objects.filter(user_id=user_id).first()
            user_display_name = org.organizer_name if org else "Organizer"
        elif role == "administrator":
            usr = UserAccount.objects.filter(user_id=user_id).first()
            user_display_name = usr.username if usr else "Admin"

    tickets_qs = Ticket.objects.select_related(
        "torder__customer", "tcategory__tevent__venue"
    ).order_by("-tcategory__tevent__event_datetime", "ticket_code")

    if role == "customer":
        tickets_qs = tickets_qs.filter(torder__customer__user_id=user_id)

    tickets = []
    for t in tickets_qs:
        tickets.append(
            (
                str(t.ticket_id),
                t.ticket_code,
                t.torder.customer.full_name,
                t.tcategory.tevent.event_title,
                t.tcategory.category_name,
                t.tcategory.price,
                t.tcategory.tevent.venue.venue_name,
                t.tcategory.tevent.venue.city,
                t.tcategory.tevent.event_datetime,
                str(t.torder.order_id),
            )
        )

    total_tiket = len(tickets)
    valid_count = total_tiket
    terpakai_count = 0

    orders_json, categories_json, seats_json = [], [], []

    if role in ["administrator", "organizer"]:
        orders_qs = Order.objects.filter(payment_status="LUNAS").select_related(
            "customer"
        )

        categories_qs = TicketCategory.objects.annotate(used=Count("ticket")).all()
        categories_json = [
            {
                "id": str(c.category_id),
                "name": c.category_name,
                "price": float(c.price),
                "quota": c.quota,
                "used": c.used,
                "event_id": str(c.tevent_id),
                "has_seat": "General" not in c.category_name,
                "display": f"{c.category_name} — Rp {c.price:,.0f} ({c.used}/{c.quota})",
            }
            for c in categories_qs
        ]

        # PERBAIKAN: Gunakan 'row_number' dan 'seat_id'
        seats_qs = Seat.objects.order_by("row_number", "seat_number")
        seats_json = [
            {
                "id": str(s.seat_id),
                "display": f"Baris {s.row_number} — Kursi {s.seat_number}",
            }
            for s in seats_qs
        ]

    context = {
        "tickets": tickets,
        "total_tiket": total_tiket,
        "valid_count": valid_count,
        "terpakai_count": terpakai_count,
        "orders_data": json.dumps(orders_json),
        "categories_data": json.dumps(categories_json),
        "seats_data": json.dumps(seats_json),
        "user_id": user_id,
        "user_name": user_display_name,
        "role": role,
        "title": (
            "Manajemen Tiket"
            if role in ["administrator", "organizer"]
            else "Tiket Saya"
        ),
    }
    return render(request, "ticket/ticket_list.html", context)


def create_ticket(request):
    if request.method == "POST":
        order_id = request.POST.get("order")
        category_id = request.POST.get("category")
        seat_id = request.POST.get("seat")

        ticket_code = f"TTK-{uuid.uuid4().hex[:8].upper()}"
        new_ticket_id = uuid.uuid4()

        try:
            ticket = Ticket.objects.create(
                ticket_id=new_ticket_id,
                ticket_code=ticket_code,
                torder_id=order_id,
                tcategory_id=category_id,
            )

            if seat_id:
                HasRelationship.objects.create(
                    ticket_id=str(new_ticket_id), seat_id=seat_id
                )

            messages.success(request, f"Tiket {ticket_code} berhasil dibuat!")
        except Exception as e:
            messages.error(request, f"Gagal membuat tiket: {e}")

    return redirect("ticket_list")


def update_ticket(request, ticket_id):
    if request.method == "POST":
        status = request.POST.get("status")
        seat_id = request.POST.get("seat")

        Ticket.objects.filter(ticket_id=ticket_id).update(
            status=status, seat_id=seat_id if seat_id else None
        )

    return redirect(request.META.get("HTTP_REFERER", "/"))


def delete_ticket(request, ticket_id):
    Ticket.objects.filter(ticket_id=ticket_id).delete()
    return redirect(request.META.get("HTTP_REFERER", "/"))


def seat_management(request):
    user_id = request.session.get("user_id")
    raw_role = get_role(user_id)

    role_display = (
        raw_role
        if raw_role in ["organizer", "customer"]
        else ("admin" if raw_role == "administrator" else "guest")
    )
    user_display_name = "Guest"

    if user_id:
        if role_display == "organizer":
            org = Organizer.objects.filter(user_id=user_id).first()
            user_display_name = org.organizer_name if org else "User"
        elif role_display == "customer":
            cust = Customer.objects.filter(user_id=user_id).first()
            user_display_name = cust.full_name if cust else "User"
        else:
            usr = UserAccount.objects.filter(user_id=user_id).first()
            user_display_name = usr.username if usr else "User"

    # PERBAIKAN: Gunakan field spesifik model seperti 'venue_name', 'row_number'
    seats_qs = (
        Seat.objects.select_related("venue")
        .annotate(is_taken=Count("hasrelationship"))
        .order_by("venue__venue_name", "section", "row_number", "seat_number")
    )

    seat_list = []
    for s in seats_qs:
        seat_list.append(
            {
                "seat_id": str(s.seat_id),
                "section": s.section,
                "row": s.row_number,
                "number": s.seat_number,
                "venue": s.venue.venue_name,
                "status": "TERISI" if s.is_taken > 0 else "TERSEDIA",
                "venue_id": str(s.venue.venue_id),
            }
        )

    total_seats = Seat.objects.count()
    total_taken = HasRelationship.objects.count()

    venues_json = []
    if role_display in ["admin", "organizer"]:
        venues_json = [
            {"id": str(v.venue_id), "nama": v.venue_name} for v in Venue.objects.all()
        ]

    context = {
        "seats": seat_list,
        "total_kursi": total_seats,
        "total_terisi": total_taken,
        "total_tersedia": total_seats - total_taken,
        "venues_data": json.dumps(venues_json),
        "user_id": user_id,
        "user_name": user_display_name,
        "role": role_display,
        "title": "Seat Inventory",
    }

    return render(request, "dashboard/seat.html", context)


def create_seat(request):
    if request.method == "POST":
        venue_id = request.POST.get("venue")
        section = request.POST.get("section")
        row = request.POST.get("row")
        seat_num = request.POST.get("seat_number")

        try:
            # PERBAIKAN: row_number=row
            Seat.objects.create(
                venue_id=venue_id, section=section, row_number=row, seat_number=seat_num
            )
            messages.success(request, "Kursi baru berhasil muncul di tabel!")
        except IntegrityError:
            messages.error(
                request, "Gagal! Kombinasi kursi di venue tersebut sudah ada."
            )

    return redirect("seat_management")


def update_seat(request, seat_id):
    if request.method == "POST":
        venue_id = request.POST.get("venue")
        section = request.POST.get("section")
        row = request.POST.get("row")
        seat_num = request.POST.get("seat_number")

        try:
            # PERBAIKAN: filter menggunakan seat_id, update ke row_number
            Seat.objects.filter(seat_id=seat_id).update(
                venue_id=venue_id, section=section, row_number=row, seat_number=seat_num
            )
            messages.success(request, "Perubahan diterapkan pada tabel!")
        except IntegrityError:
            messages.error(request, "Gagal update! Data mungkin duplikat.")

    return redirect("seat_management")


def delete_seat(request, seat_id):
    # PERBAIKAN: filter menggunakan seat_id
    if HasRelationship.objects.filter(seat_id=seat_id).exists():
        messages.error(
            request,
            "Kursi ini sudah di-assign ke tiket dan tidak dapat dihapus. Hapus atau ubah tiket terlebih dahulu.",
        )
    else:
        Seat.objects.filter(seat_id=seat_id).delete()
        messages.success(request, "Kursi berhasil dihapus.")

    return redirect("seat_management")
