from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import connection, IntegrityError
from django.db.models import Count, Sum
from django.utils import timezone
from django.db import IntegrityError
from django.contrib.auth import get_user_model
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
    if "user_id" not in request.session:
        messages.error(request, "Silakan login untuk melihat daftar artis.")
        return redirect("login")

    return render(request, "artist/artist.html")


def create_artist(request):
    # CREATE: Hanya Admin
    if request.session.get("role") != "administrator":
        return redirect("artist_list")
    # ... logika simpan data artis ...
    pass


def update_artist(request, artist_id):
    # UPDATE: Hanya Admin
    if request.session.get("role") != "administrator":
        return redirect("artist_list")
    # ... logika update data artis ...
    pass


def delete_artist(request, artist_id):
    # DELETE: Hanya Admin
    if request.session.get("role") != "administrator":
        return redirect("artist_list")
    # ... logika hapus data artis ...
    pass


def ticket_category_list_view(request):
    return render(request, "ticket/ticket-category.html")


def create_ticket_category(request):
    # CREATE: Hanya Admin dan Organizer
    role = request.session.get("role")
    if role not in ["administrator", "organizer"]:
        return redirect("ticket_category_list")
    # ... logika simpan kategori tiket ...
    pass


def update_ticket_category(request, category_id):
    # UPDATE: Hanya Admin dan Organizer
    role = request.session.get("role")
    if role not in ["administrator", "organizer"]:
        return redirect("ticket_category_list")
    # ... logika update kategori tiket ...
    pass


def delete_ticket_category(request, category_id):
    # DELETE: Hanya Admin dan Organizer
    role = request.session.get("role")
    if role not in ["administrator", "organizer"]:
        return redirect("ticket_category_list")
    # ... logika hapus kategori tiket ...
    pass


def get_role(user_id):
    if not user_id:
        return "guest"
    try:
        # Use .first() instead of .get() to handle users with multiple roles safely
        account_role = (
            AccountRole.objects.select_related("role").filter(user_id=user_id).first()
        )
        return account_role.role.role_name.lower() if account_role else "guest"
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

    # Get role from session first (from role selection), fallback to database
    raw_role_name = request.session.get("role") or get_role(user_id)

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
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO tiktaktuk, public")

        cursor.execute("DELETE FROM TICKET WHERE ticket_id = %s", [ticket_id])

    return redirect(request.META.get("HTTP_REFERER", "/"))


def seat_management(request, user_id=None):
    """
    Halaman List Kursi: Bisa dibaca semua role (Guest, Customer, Organizer, Admin).
    Aksi CUD: Hanya muncul untuk Admin & Organizer.
    """
    current_user_id = user_id or request.session.get("user_id")

    # Identifikasi Role
    raw_role = get_role(current_user_id)

    # Mapping Role
    if raw_role == "administrator":
        role_display = "admin"
    elif raw_role == "organizer":
        role_display = "organizer"
    elif raw_role == "customer":
        role_display = "customer"
    else:
        role_display = "guest"

    seat_base_path = (
        f"/dashboard/{current_user_id}/seat" if current_user_id else "/dashboard/seat"
    )
    seat_create_url = f"{seat_base_path}/create/"
    seat_update_base_url = f"{seat_base_path}/update/"
    seat_delete_base_url = f"{seat_base_path}/delete/"

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO tiktaktuk, public")

        # Nama User untuk Greeting
        user_display_name = "Guest"
        if current_user_id:
            if role_display == "organizer":
                cursor.execute(
                    "SELECT organizer_name FROM ORGANIZER WHERE user_id = %s",
                    [current_user_id],
                )
            elif role_display == "customer":
                cursor.execute(
                    "SELECT full_name FROM CUSTOMER WHERE user_id = %s",
                    [current_user_id],
                )
            else:
                cursor.execute(
                    "SELECT username FROM USER_ACCOUNT WHERE user_id = %s",
                    [current_user_id],
                )

            row_name = cursor.fetchone()
            user_display_name = row_name[0] if row_name else "User"

        # read
        cursor.execute("""
            SELECT 
                s.seat_id, s.section, s.row_number, s.seat_number, v.venue_name,
                CASE 
                    WHEN hr.seat_id IS NOT NULL THEN 'TERISI'
                    ELSE 'TERSEDIA'
                END as status,
                v.venue_id
            FROM SEAT s
            JOIN VENUE v ON s.venue_id = v.venue_id
            LEFT JOIN HAS_RELATIONSHIP hr ON s.seat_id = hr.seat_id
            ORDER BY v.venue_name, s.section, s.row_number, s.seat_number
        """)
        rows = cursor.fetchall()

        seat_list = []
        for r in rows:
            seat_list.append(
                {
                    "seat_id": str(r[0]),
                    "section": r[1],
                    "row": r[2],
                    "number": r[3],
                    "venue": r[4],
                    "status": r[5],
                    "venue_id": str(r[6]),
                }
            )

        # Statistik Dashboard
        cursor.execute("SELECT COUNT(*) FROM SEAT")
        total_seats = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM HAS_RELATIONSHIP")
        total_taken = cursor.fetchone()[0] or 0

        # Data Venue (Admin/Org untuk Modal)
        venues_json = []
        if role_display in ["admin", "organizer"]:
            cursor.execute("SELECT venue_id, venue_name FROM VENUE")
            venues_json = [{"id": str(v[0]), "nama": v[1]} for v in cursor.fetchall()]

    # Kirim Context
    context = {
        "seats": seat_list,
        "total_kursi": total_seats,
        "total_terisi": total_taken,
        "total_tersedia": total_seats - total_taken,
        "seat_create_url": seat_create_url,
        "seat_update_base_url": seat_update_base_url,
        "seat_delete_base_url": seat_delete_base_url,
        "venues_data": json.dumps(venues_json),
        "user_id": current_user_id,
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


def delete_seat(request, user_id, seat_id):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO tiktaktuk, public")

            cursor.execute(
                "SELECT 1 FROM HAS_RELATIONSHIP WHERE seat_id = %s", [seat_id]
            )
            if cursor.fetchone():
                messages.error(
                    request,
                    "Kursi ini sudah di-assign ke tiket dan tidak dapat dihapus. Hapus atau ubah tiket terlebih dahulu.",
                )
            else:
                cursor.execute("DELETE FROM SEAT WHERE seat_id = %s", [seat_id])
                messages.success(request, "Kursi berhasil dihapus.")
    except Exception as e:
        messages.error(request, f"Terjadi kesalahan: {e}")

    return redirect("seat_management", user_id=user_id)


def venue_list(request):
    role = request.GET.get("role", "customer")

    venues = [
        {
            "id": 1,
            "name": "Jakarta Convention Center",
            "address": "Jl. Gatot Subroto No.1, Jakarta",
            "city": "Jakarta",
            "capacity": 1000,
            "has_reserved_seating": True,
        },
        {
            "id": 2,
            "name": "Taman Impian Jaya Ancol",
            "address": "Jl. Lodan Timur No.7, Jakarta Utara",
            "city": "Jakarta",
            "capacity": 500,
            "has_reserved_seating": False,
        },
    ]

    total_capacity = sum(v["capacity"] for v in venues)
    reserved_count = sum(1 for v in venues if v["has_reserved_seating"])

    return render(
        request,
        "venue/venue_list.html",
        {
            "role": role,
            "venues": venues,
            "total_capacity": total_capacity,
            "reserved_count": reserved_count,
        },
    )


semua_dummy_event = [
    {
        "title": "Konser Melodi Senja",
        "date": "2026-05-15",
        "time": "19:00",
        "venue": "Jakarta Convention Center",
        "artists": ["Fourtwnty", "Hindia"],
        "price": "250.000",
        "categories": ["VIP"],
        "icon": "🎵",
        "organizer_id": 1,
        "description": "Nikmati suasana senja dengan alunan musik indie.",
    },
    {
        "title": "Festival Seni Budaya",
        "date": "2026-05-22",
        "time": "10:00",
        "venue": "Taman Impian Jaya Ancol",
        "artists": ["Tulus"],
        "price": "150.000",
        "categories": ["Regular"],
        "icon": "🎨",
        "organizer_id": 1,
        "description": "Festival seni dan budaya untuk semua kalangan.",
    },
    {
        "title": "Malam Akustik Bandung",
        "date": "2026-06-10",
        "time": "18:00",
        "venue": "Bandung Hall Center",
        "artists": ["Pamungkas", "Nadin Amizah"],
        "price": "350.000",
        "categories": ["VIP", "Regular"],
        "icon": "🎸",
        "organizer_id": 2,
        "description": "Malam musik akustik di Bandung.",
    },
]


def event_list(request):
    # Customer: semua event, tombol beli tiket
    events = semua_dummy_event
    return render(
        request,
        "event/event_list.html",
        {
            "role": "customer",
            "events": events,
        },
    )


def admin_event_list(request):
    events = semua_dummy_event

    return render(
        request,
        "event/my_event_list.html",
        {
            "events": events,
            "role": "admin",
        },
    )


def my_event_list(request):
    events = [e for e in semua_dummy_event if e["organizer_id"] == 1]

    return render(
        request,
        "event/my_event_list.html",
        {
            "events": events,
            "role": "organizer",
        },
    )


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

User = get_user_model()

# ==========================================
# VARIABEL INI BUAT NGETES UI 
# Pilihan: 'Admin', 'Organizer', atau 'Customer'
# ==========================================
SIMULASI_ROLE = 'Admin' 

def checkout_view(request):
    ticket_prices = {
        'WVIP': 1500000,
        'VIP': 750000,
        'Category 1': 450000,
        'Category 2': 250000
    }

    if request.method == 'POST':
        category = request.POST.get('ticket_category')
        quantity = int(request.POST.get('quantity', 0))
        seat = request.POST.get('seat', '')
        promo = request.POST.get('promo_code', '')

        if category not in ticket_prices:
            messages.error(request, "Pilih kategori tiket yang valid.")
            return redirect('checkout')

        if quantity <= 0 or quantity > 10:
            messages.error(request, "Jumlah tiket harus antara 1 - 10 per transaksi.")
            return redirect('checkout')

        base_price = ticket_prices[category]
        total_price = base_price * quantity

        if promo == 'TIKTAK20':
            total_price = total_price * 0.8
        elif promo and promo != 'TIKTAK20':
            messages.error(request, "Kode promo tidak valid.")
            return redirect('checkout')
        dummy_user = User.objects.first() 
        
        if dummy_user:
            Order.objects.create(
                customer=dummy_user,
                total_amount=total_price,
                ticket_category=category,
                quantity=quantity,
                seat_number=seat,
                promo_code=promo,
                payment_status='Pending'
            )
            messages.success(request, "Pesanan berhasil dibuat!")
        else:
            messages.error(request, "Gagal save: Belum ada user sama sekali di database.")

        return redirect('daftar_order') 

    return render(request, 'order/checkout.html')


def daftar_order_view(request):
    orders = Order.objects.all().order_by('-order_date')
    total_order = orders.count()
    lunas_count = orders.filter(payment_status='Paid').count()
    pending_count = orders.filter(payment_status='Pending').count()
    
    total_revenue = 0
    if SIMULASI_ROLE in ['Admin', 'Organizer']:
        revenue_aggr = orders.filter(payment_status='Paid').aggregate(Sum('total_amount'))
        total_revenue = revenue_aggr['total_amount__sum'] or 0

    context = {
        'orders': orders,
        'total_order': total_order,
        'lunas_count': lunas_count,
        'pending_count': pending_count,
        'total_revenue': total_revenue,
        'user_role': SIMULASI_ROLE,
    }
    return render(request, 'order/order_list.html', context)

def update_order_status(request, order_id):
    if SIMULASI_ROLE != 'Admin':
        messages.error(request, "Akses ditolak!")
        return redirect('daftar_order')

    order = get_object_or_404(Order, order_id=order_id)
    if request.method == 'POST':
        new_status = request.POST.get('payment_status')
        order.payment_status = new_status
        order.save()
        messages.success(request, f"Status Order {order_id} berhasil diperbarui!")
        
    return redirect('daftar_order')

def delete_order(request, order_id):
    if SIMULASI_ROLE != 'Admin':
        messages.error(request, "Akses ditolak!")
        return redirect('daftar_order')

    order = get_object_or_404(Order, order_id=order_id)
    if request.method == 'POST':
        order.delete()
        messages.success(request, f"Data Order {order_id} berhasil dihapus!")
        
    return redirect('daftar_order')

def promotion_list_view(request):
    promotions = Promotion.objects.all().order_by('-start_date') 
    
    context = {
        'promotions': promotions,
        'user_role': SIMULASI_ROLE,
    }
    return render(request, 'promotion/promotion_list.html', context)

def create_promotion(request):
    if SIMULASI_ROLE != 'Admin':
        messages.error(request, "Akses ditolak!")
        return redirect('promotion_list')
        
    if request.method == 'POST':
        Promotion.objects.create(
            promo_code=request.POST.get('promo_code').upper(),
            discount_type=request.POST.get('discount_type'),
            discount_value=request.POST.get('discount_value'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            usage_limit=request.POST.get('usage_limit')
        )
        messages.success(request, "Promo baru berhasil dibuat!")
    return redirect('promotion_list')

def update_promotion(request, promo_id):
    if SIMULASI_ROLE != 'Admin':
        messages.error(request, "Akses ditolak!")
        return redirect('promotion_list')

    promo = get_object_or_404(Promotion, promotion_id=promo_id)
    if request.method == 'POST':
        promo.promo_code = request.POST.get('promo_code').upper()
        promo.discount_type = request.POST.get('discount_type')
        promo.discount_value = request.POST.get('discount_value')
        promo.start_date = request.POST.get('start_date')
        promo.end_date = request.POST.get('end_date')
        promo.usage_limit = request.POST.get('usage_limit')
        promo.save()
        messages.success(request, "Data promo berhasil diperbarui!")
        
    return redirect('promotion_list')

def delete_promotion(request, promo_id):
    if SIMULASI_ROLE != 'Admin':
        messages.error(request, "Akses ditolak!")
        return redirect('promotion_list')

    promo = get_object_or_404(Promotion, promotion_id=promo_id)
    if request.method == 'POST':
        promo.delete()
        messages.success(request, "Data promo berhasil dihapus!")
        
    return redirect('promotion_list')