import uuid, json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Sum
from django.db.models import Count, Sum, Min
from django.utils import timezone
from django.db import IntegrityError, DatabaseError, connection, transaction
from django.contrib.auth import get_user_model
import uuid, json
from django.db.models.functions import Lower
from datetime import datetime

from .models import (
    Venue,
    Seat,
    HasRelationship,
    Event,
    Ticket,
    TicketCategory,
    Order,
    Promotion,
    Artist,
    EventArtist,
)
from authentication.models import UserAccount, AccountRole, Customer, Organizer


def home_view(request):
    return redirect("dashboard")


def artist_list_view(request):
    # RBAC Read: Hanya pengguna yang sudah login
    if "user_id" not in request.session:
        messages.error(request, "Silakan login untuk melihat daftar artis.")
        return redirect("auth:login")

    role = request.session.get("role", "guest")
    search_query = request.GET.get("q", "").strip()  # Ambil parameter 'q'

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")

        if search_query:
            # Menggunakan ILIKE untuk pencarian case-insensitive pada name atau genre
            search_param = f"%{search_query}%"
            cursor.execute(
                """
                SELECT artist_id, name, genre 
                FROM ARTIST 
                WHERE name ILIKE %s OR genre ILIKE %s
                ORDER BY name ASC
            """,
                [search_param, search_param],
            )
        else:
            cursor.execute(
                "SELECT artist_id, name, genre FROM ARTIST ORDER BY name ASC"
            )

        artists = [
            {"artist_id": str(row[0]), "name": row[1], "genre": row[2]}
            for row in cursor.fetchall()
        ]

    context = {
        "artists": artists,
        "role": role,
        "search_query": search_query,  # Kirim kembali ke template untuk mempertahankan input
    }
    return render(request, "artist/artist.html", context)


def create_artist(request):
    # RBAC Create: Hanya Administrator
    if request.session.get("role") != "administrator":
        messages.error(request, "Akses ditolak! Hanya Admin yang dapat menambah artis.")
        return redirect("artist_list")

    if request.method == "POST":
        name = request.POST.get("name")
        genre = request.POST.get("genre")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    "INSERT INTO ARTIST (name, genre) VALUES (%s, %s)", [name, genre]
                )
            messages.success(request, "Artis berhasil ditambahkan!")
        except Exception as e:
            messages.error(request, f"Gagal menambahkan artis: {e}")

    return redirect("artist_list")


def update_artist(request, artist_id):
    # RBAC Update: Hanya Administrator
    if request.session.get("role") != "administrator":
        messages.error(request, "Akses ditolak! Hanya Admin yang dapat mengubah artis.")
        return redirect("artist_list")

    if request.method == "POST":
        name = request.POST.get("name")
        genre = request.POST.get("genre")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    "UPDATE ARTIST SET name = %s, genre = %s WHERE artist_id = %s",
                    [name, genre, artist_id],
                )
            messages.success(request, "Data artis berhasil diperbarui!")
        except Exception as e:
            messages.error(request, f"Gagal memperbarui artis: {e}")

    return redirect("artist_list")


def delete_artist(request, artist_id):
    # RBAC Delete: Hanya Administrator
    if request.session.get("role") != "administrator":
        messages.error(
            request, "Akses ditolak! Hanya Admin yang dapat menghapus artis."
        )
        return redirect("artist_list")

    if request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute("DELETE FROM ARTIST WHERE artist_id = %s", [artist_id])
            messages.success(request, "Artis berhasil dihapus!")
        except Exception as e:
            messages.error(request, f"Gagal menghapus artis: {e}")

    return redirect("artist_list")


def ticket_category_list_view(request):
    # RBAC Read: Guest (belum login) dan semua role bisa melihat
    role = request.session.get("role", "guest")
    user_id = request.session.get("user_id")
    search_query = request.GET.get("q", "").strip()

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")

        # Base query
        base_sql = """
            SELECT tc.category_id, tc.category_name, tc.quota, tc.price, tc.tevent_id, e.event_title
            FROM TICKET_CATEGORY tc
            JOIN EVENT e ON tc.tevent_id = e.event_id
        """

        if search_query:
            search_param = f"%{search_query}%"
            base_sql += " WHERE tc.category_name ILIKE %s OR e.event_title ILIKE %s"
            base_sql += " ORDER BY e.event_datetime DESC, tc.price DESC"
            cursor.execute(base_sql, [search_param, search_param])
        else:
            base_sql += " ORDER BY e.event_datetime DESC, tc.price DESC"
            cursor.execute(base_sql)

        categories = [
            {
                "category_id": str(row[0]),
                "category_name": row[1],
                "quota": row[2],
                "price": row[3],
                "tevent_id": str(row[4]),
                "event_title": row[5],
            }
            for row in cursor.fetchall()
        ]

        # Fetch list Event untuk dropdown filter/tambah data di frontend
        events = []
        if role in ["administrator", "organizer"]:
            if role == "organizer" and user_id:
                cursor.execute(
                    "SELECT organizer_id FROM ORGANIZER WHERE user_id = %s", [user_id]
                )
                org_row = cursor.fetchone()
                if org_row:
                    cursor.execute(
                        "SELECT event_id, event_title FROM EVENT WHERE organizer_id = %s",
                        [org_row[0]],
                    )
                    events = [
                        {"event_id": str(r[0]), "event_title": r[1]}
                        for r in cursor.fetchall()
                    ]
            else:
                cursor.execute("SELECT event_id, event_title FROM EVENT")
                events = [
                    {"event_id": str(r[0]), "event_title": r[1]}
                    for r in cursor.fetchall()
                ]

    context = {
        "categories": categories,
        "events": events,
        "role": role,
        "search_query": search_query,
    }
    return render(request, "ticket/ticket-category.html", context)


def create_ticket_category(request):
    # RBAC Create: Administrator & Organizer
    role = request.session.get("role")
    if role not in ["administrator", "organizer"]:
        messages.error(request, "Akses ditolak! Anda tidak memiliki izin.")
        return redirect("ticket_category_list")

    if request.method == "POST":
        category_name = request.POST.get("category_name")
        quota = request.POST.get("quota")
        price = request.POST.get("price")
        tevent_id = request.POST.get("tevent_id")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    INSERT INTO TICKET_CATEGORY (category_name, quota, price, tevent_id)
                    VALUES (%s, %s, %s, %s)
                """,
                    [category_name, quota, price, tevent_id],
                )
            messages.success(request, "Kategori tiket berhasil ditambahkan!")
        except Exception as e:
            messages.error(request, f"Gagal menambahkan kategori tiket: {e}")

    return redirect("ticket_category_list")


def update_ticket_category(request, category_id):
    # RBAC Update: Administrator & Organizer
    role = request.session.get("role")
    if role not in ["administrator", "organizer"]:
        messages.error(request, "Akses ditolak! Anda tidak memiliki izin.")
        return redirect("ticket_category_list")

    if request.method == "POST":
        category_name = request.POST.get("category_name")
        quota = request.POST.get("quota")
        price = request.POST.get("price")
        tevent_id = request.POST.get("tevent_id")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    UPDATE TICKET_CATEGORY
                    SET category_name = %s, quota = %s, price = %s, tevent_id = %s
                    WHERE category_id = %s
                """,
                    [category_name, quota, price, tevent_id, category_id],
                )
            messages.success(request, "Kategori tiket berhasil diperbarui!")
        except Exception as e:
            messages.error(request, f"Gagal memperbarui kategori tiket: {e}")

    return redirect("ticket_category_list")


def delete_ticket_category(request, category_id):
    # RBAC Delete: Administrator & Organizer
    role = request.session.get("role")
    if role not in ["administrator", "organizer"]:
        messages.error(request, "Akses ditolak! Anda tidak memiliki izin.")
        return redirect("ticket_category_list")

    if request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    "DELETE FROM TICKET_CATEGORY WHERE category_id = %s", [category_id]
                )
            messages.success(request, "Kategori tiket berhasil dihapus!")
        except Exception as e:
            messages.error(request, f"Gagal menghapus kategori tiket: {e}")

    return redirect("ticket_category_list")


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
        "user_id": str(current_user_id) if current_user_id else "",
        "user_name": user_display_name,
        "role": role_display,
        "title": "Seat Inventory",
    }

    return render(request, "dashboard/seat.html", context)

def create_seat(request, user_id):
    if request.method == "POST":
        v_id = request.POST.get("venue")
        sec = request.POST.get("section")
        row = request.POST.get("row")
        s_num = request.POST.get("seat_number")

        if not s_num or not s_num.isdigit() or int(s_num) < 1:
            messages.error(request, f"No. kursi '{s_num}' tidak valid!")
            return redirect("seat_management", user_id=user_id)

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO tiktaktuk, public")
                cursor.execute("""
                    INSERT INTO SEAT (venue_id, section, row_number, seat_number)
                    VALUES (%s, %s, %s, %s)
                """, [v_id, sec, row, s_num])
            messages.success(request, "Kursi berhasil ditambahkan!")
        except IntegrityError:
            messages.error(request, "Gagal! Kombinasi kursi sudah ada di venue ini.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return redirect("seat_management", user_id=user_id)

def update_seat(request, user_id, seat_id):
    if request.method == "POST":
        v_id = request.POST.get("venue")
        sec = request.POST.get("section")
        row = request.POST.get("row")
        s_num = request.POST.get("seat_number")

        if not s_num or not s_num.isdigit() or int(s_num) < 1:
            messages.error(request, f"No. kursi '{s_num}' tidak valid!")
            return redirect("seat_management", user_id=user_id)

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO tiktaktuk, public")
                cursor.execute("""
                    UPDATE SEAT SET venue_id=%s, section=%s, row_number=%s, seat_number=%s
                    WHERE seat_id=%s
                """, [v_id, sec, row, s_num, seat_id])
            messages.success(request, "Perubahan berhasil disimpan!")
        except IntegrityError:
            messages.error(request, "Gagal update! Data mungkin duplikat.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return redirect("seat_management", user_id=user_id)

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

    return redirect('seat_management', user_id=user_id)

def clean_db_error(e):
    return str(e).split("CONTEXT:")[0].strip()

def normalize_role(raw_role):
    if raw_role == "administrator":
        return "admin"
    if raw_role in ["admin", "organizer", "customer"]:
        return raw_role
    return "customer"


def get_current_role(request):
    user_id = request.session.get("user_id")
    if user_id:
        return normalize_role(request.session.get("role") or get_role(user_id))
    return normalize_role(request.GET.get("role", "customer"))


def venue_list(request):
    role = get_current_role(request)

    venues_qs = Venue.objects.all().order_by("city", "venue_name")

    venues = []
    for v in venues_qs:
        venues.append({
            "id": str(v.venue_id),
            "name": v.venue_name,
            "address": v.address,
            "city": v.city,
            "capacity": v.capacity,
            "jenis_seating": v.jenis_seating,
            "has_reserved_seating": v.jenis_seating == "Reserved Seating",
        })

    total_capacity = venues_qs.aggregate(total=Sum("capacity"))["total"] or 0
    reserved_count = venues_qs.filter(jenis_seating="Reserved Seating").count()

    return render(request, "venue/venue_list.html", {
        "role": role,
        "venues": venues,
        "total_capacity": total_capacity,
        "reserved_count": reserved_count,
    })

def create_venue(request):
    role = get_current_role(request)
    if role not in ["admin", "organizer"]:
        messages.error(request, "Anda tidak memiliki akses untuk menambah venue.")
        return redirect("venue_list")

    if request.method == "POST":
        name = request.POST.get("venue_name", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        capacity = request.POST.get("capacity")
        has_reserved = request.POST.get("has_reserved_seating") == "on"

        jenis_seating = "Reserved Seating" if has_reserved else "Free Seating"

        duplicate = Venue.objects.filter(
            venue_name__iexact=name,
            city__iexact=city
        ).first()

        if duplicate:
            messages.error(
                request,
                f'ERROR: Venue "{name}" di kota "{city}" sudah terdaftar dengan ID {duplicate.venue_id}.'
            )
            return redirect("venue_list")

        try:
            Venue.objects.create(
                venue_id=uuid.uuid4(),
                venue_name=name,
                address=address,
                city=city,
                capacity=capacity,
                jenis_seating=jenis_seating,
            )

            messages.success(request, "Venue berhasil ditambahkan.")

        except DatabaseError as e:
            messages.error(request, clean_db_error(e))

        return redirect("venue_list")


def update_venue(request, venue_id):
    role = get_current_role(request)
    if role not in ["admin", "organizer"]:
        messages.error(request, "Anda tidak memiliki akses untuk mengubah venue.")
        return redirect("venue_list")

    venue = get_object_or_404(Venue, venue_id=venue_id)

    if request.method == "POST":
        name = request.POST.get("venue_name", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        capacity = request.POST.get("capacity")
        has_reserved = request.POST.get("has_reserved_seating") == "on"

        jenis_seating = "Reserved Seating" if has_reserved else "Free Seating"

        duplicate = Venue.objects.filter(
            venue_name__iexact=name,
            city__iexact=city
        ).exclude(venue_id=venue_id).first()

        if duplicate:
            messages.error(
                request,
                f'ERROR: Venue "{name}" di kota "{city}" sudah terdaftar dengan ID {duplicate.venue_id}.'
            )
            return redirect("venue_list")

        venue.venue_name = name
        venue.address = address
        venue.city = city
        venue.capacity = capacity
        venue.jenis_seating = jenis_seating
        try:
            venue.save()
            messages.success(request, "Venue berhasil diperbarui.")

        except DatabaseError as e:
            messages.error(request, clean_db_error(e))

        return redirect("venue_list")


def delete_venue(request, venue_id):
    role = get_current_role(request)
    if role not in ["admin", "organizer"]:
        messages.error(request, "Anda tidak memiliki akses untuk menghapus venue.")
        return redirect("venue_list")

    venue = get_object_or_404(Venue, venue_id=venue_id)

    has_active_event = Event.objects.filter(
        venue=venue,
        event_datetime__gte=timezone.now()
    ).exists()

    if has_active_event:
        messages.error(
            request,
            f'ERROR: Venue "{venue.venue_name}" masih memiliki event aktif sehingga tidak dapat dihapus.'
        )
        return redirect("venue_list")

    try:
        venue.delete()
        messages.success(request, "Venue berhasil dihapus.")

    except DatabaseError as e:
        messages.error(request, clean_db_error(e))
    return redirect("venue_list")

def format_event(e):
    categories = list(e.ticketcategory_set.all())
    artists = [
    ea.artist.name
    for ea in EventArtist.objects.filter(event=e).select_related("artist")
    ]

    min_price = min([c.price for c in categories], default=0)

    return {
        "id": str(e.event_id),
        "title": e.event_title,
        "date": e.event_datetime.strftime("%Y-%m-%d"),
        "time": e.event_datetime.strftime("%H:%M"),
        "venue": e.venue.venue_name,
        "venue_id": str(e.venue.venue_id),
        "artists": artists,
        "price": f"{min_price:,.0f}".replace(",", "."),
        "categories": [c.category_name for c in categories],
        "icon": "🎵",
        "organizer_id": str(e.organizer_id),
    }


def event_list(request):
    events_qs = (
        Event.objects
        .select_related("venue", "organizer")
        .prefetch_related("ticketcategory_set")
        .order_by("event_datetime")
    )

    search = request.GET.get("search")
    venue_id = request.GET.get("venue")
    artist_id = request.GET.get("artist")

    if search:
        events_qs = events_qs.filter(event_title__icontains=search)

    if venue_id:
        events_qs = events_qs.filter(venue_id=venue_id)

    if artist_id:
        event_ids = EventArtist.objects.filter(artist_id=artist_id).values_list("event_id", flat=True)
        events_qs = events_qs.filter(event_id__in=event_ids)

    events = [format_event(e) for e in events_qs.distinct()]

    return render(request, "event/event_list.html", {
        "role": get_current_role(request),
        "events": events,
        "venues": Venue.objects.all(),
        "artists": Artist.objects.all(),
    })


def admin_event_list(request):
    events_qs = (
        Event.objects
        .select_related("venue", "organizer")
        .prefetch_related("ticketcategory_set")
        .order_by("event_datetime")
    )

    events = [format_event(e) for e in events_qs]

    return render(request, "event/my_event_list.html", {
        "role": "admin",
        "events": events,
        "venues": Venue.objects.all(),
        "organizers": Organizer.objects.all(),
        "artists": Artist.objects.all(),
    })


def my_event_list(request):
    user_id = request.session.get("user_id")
    role = get_current_role(request)

    if role != "organizer":
        messages.error(request, "Anda harus login sebagai organizer untuk mengakses halaman ini.")
        return redirect("event_list")

    organizer = Organizer.objects.filter(user_id=user_id).first()

    if not organizer:
        messages.error(request, "Data organizer tidak ditemukan.")
        return redirect("event_list")

    events_qs = (
        Event.objects
        .filter(organizer=organizer)
        .select_related("venue", "organizer")
        .prefetch_related("ticketcategory_set")
        .order_by("event_datetime")
    )

    events = [format_event(e) for e in events_qs]

    return render(request, "event/my_event_list.html", {
        "role": "organizer",
        "events": events,
        "venues": Venue.objects.all(),
        "artists": Artist.objects.all(),
    })

def save_event_artists(event, artist_ids):
    EventArtist.objects.filter(event=event).delete()

    for artist_id in artist_ids:
        if artist_id:
            EventArtist.objects.create(
                event=event,
                artist_id=artist_id,
            )


def save_event_categories(event, names, prices, quotas):
    TicketCategory.objects.filter(tevent=event).delete()

    for name, price, quota in zip(names, prices, quotas):
        if name and price and quota:
            TicketCategory.objects.create(
                category_id=uuid.uuid4(),
                category_name=name,
                price=price,
                quota=quota,
                tevent=event,
            )

def create_event(request):
    role = get_current_role(request)
    if role not in ["admin", "organizer"]:
        messages.error(request, "Anda tidak memiliki akses untuk membuat event.")
        return redirect("event_list")

    if request.method == "POST":
        title = request.POST.get("event_title", "").strip()
        date = request.POST.get("date")
        time = request.POST.get("time")
        venue_id = request.POST.get("venue_id")

        artist_ids = request.POST.getlist("artist_ids")
        category_names = request.POST.getlist("category_name")
        category_prices = request.POST.getlist("category_price")
        category_quotas = request.POST.getlist("category_quota")

        try:
            event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

            if role == "organizer":
                organizer = Organizer.objects.filter(user_id=request.session.get("user_id")).first()
                if not organizer:
                    messages.error(request, "Data organizer tidak ditemukan.")
                    return redirect("event_list")
            else:
                organizer = Organizer.objects.first()
                if not organizer:
                    messages.error(request, "Belum ada organizer yang tersedia.")
                    return redirect("admin_event_list")

            with transaction.atomic():
                event = Event.objects.create(
                    event_id=uuid.uuid4(),
                    event_title=title,
                    event_datetime=event_datetime,
                    venue_id=venue_id,
                    organizer=organizer,
                )

                save_event_artists(event, artist_ids)
                save_event_categories(event, category_names, category_prices, category_quotas)

            messages.success(request, "Event berhasil dibuat.")

        except DatabaseError as e:
            messages.error(request, clean_db_error(e))
        except Exception as e:
            messages.error(request, f"Gagal membuat event: {e}")

    return redirect("my_event_list" if role == "organizer" else "admin_event_list")

def update_event(request, event_id):
    role = get_current_role(request)
    event = get_object_or_404(Event, event_id=event_id)

    if role not in ["admin", "organizer"]:
        messages.error(request, "Anda tidak memiliki akses untuk mengubah event.")
        return redirect("event_list")

    if role == "organizer":
        organizer = Organizer.objects.filter(user_id=request.session.get("user_id")).first()
        if event.organizer != organizer:
            messages.error(request, "Organizer hanya dapat mengubah event miliknya sendiri.")
            return redirect("my_event_list")

    if request.method == "POST":
        title = request.POST.get("event_title", "").strip()
        date = request.POST.get("date")
        time = request.POST.get("time")
        venue_id = request.POST.get("venue_id")

        artist_ids = request.POST.getlist("artist_ids")
        category_names = request.POST.getlist("category_name")
        category_prices = request.POST.getlist("category_price")
        category_quotas = request.POST.getlist("category_quota")

        try:
            with transaction.atomic():
                event.event_title = title
                event.event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                event.venue_id = venue_id
                event.save()

                save_event_artists(event, artist_ids)
                save_event_categories(event, category_names, category_prices, category_quotas)

            messages.success(request, "Event berhasil diperbarui.")

        except DatabaseError as e:
            messages.error(request, clean_db_error(e))
        except Exception as e:
            messages.error(request, f"Gagal memperbarui event: {e}")

    return redirect("my_event_list" if role == "organizer" else "admin_event_list")


User = get_user_model()

# ==========================================
# VARIABEL INI BUAT NGETES UI
# Pilihan: 'Admin', 'Organizer', atau 'Customer'
# ==========================================
SIMULASI_ROLE = "Admin"


def checkout_view(request):
    ticket_prices = {
        "WVIP": 1500000,
        "VIP": 750000,
        "Category 1": 450000,
        "Category 2": 250000,
    }

    if request.method == "POST":
        category = request.POST.get("ticket_category")
        quantity = int(request.POST.get("quantity", 0))
        seat = request.POST.get("seat", "")
        promo = request.POST.get("promo_code", "")

        if category not in ticket_prices:
            messages.error(request, "Pilih kategori tiket yang valid.")
            return redirect("checkout")

        if quantity <= 0 or quantity > 10:
            messages.error(request, "Jumlah tiket harus antara 1 - 10 per transaksi.")
            return redirect("checkout")

        base_price = ticket_prices[category]
        total_price = base_price * quantity

        if promo == "TIKTAK20":
            total_price = total_price * 0.8
        elif promo and promo != "TIKTAK20":
            messages.error(request, "Kode promo tidak valid.")
            return redirect("checkout")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                # Simulasi mengambil customer_id pertama dari database
                cursor.execute("SELECT customer_id FROM CUSTOMER LIMIT 1")
                cust_row = cursor.fetchone()

                if cust_row:
                    # Insert Order menggunakan raw query
                    cursor.execute(
                        """
                        INSERT INTO "ORDER" (order_date, payment_status, total_amount, customer_id)
                        VALUES (NOW(), 'Pending', %s, %s)
                    """,
                        [total_price, cust_row[0]],
                    )
                    messages.success(request, "Pesanan berhasil dibuat!")
                else:
                    messages.error(
                        request,
                        "Gagal save: Belum ada customer sama sekali di database.",
                    )
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat memproses pesanan: {e}")

        return redirect("daftar_order")

    return render(request, "order/checkout.html")


def daftar_order_view(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")

            cursor.execute("""
                SELECT order_id, order_date, payment_status, total_amount, customer_id 
                FROM "ORDER" ORDER BY order_date DESC
            """)
            orders = cursor.fetchall()

            cursor.execute('SELECT COUNT(*) FROM "ORDER"')
            total_order = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM \"ORDER\" WHERE payment_status = 'LUNAS'"
            )
            lunas_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM \"ORDER\" WHERE payment_status = 'PENDING'"
            )
            pending_count = cursor.fetchone()[0]

            total_revenue = 0
            if SIMULASI_ROLE in ["Admin", "Organizer"]:
                cursor.execute(
                    "SELECT SUM(total_amount) FROM \"ORDER\" WHERE payment_status = 'LUNAS'"
                )
                revenue_res = cursor.fetchone()[0]
                total_revenue = revenue_res if revenue_res else 0

            # Transform raw tuple ke dictionary agar template tetap bisa render
            orders_dict = [
                {
                    "order_id": row[0],
                    "order_date": row[1],
                    "payment_status": row[2],
                    "total_amount": row[3],
                    "customer_id": row[4],
                }
                for row in orders
            ]

    except Exception as e:
        orders_dict = []
        total_order = lunas_count = pending_count = total_revenue = 0

    context = {
        "orders": orders_dict,
        "total_order": total_order,
        "lunas_count": lunas_count,
        "pending_count": pending_count,
        "total_revenue": total_revenue,
        "user_role": SIMULASI_ROLE,
    }
    return render(request, "order/order_list.html", context)


def update_order_status(request, order_id):
    if SIMULASI_ROLE != "Admin":
        messages.error(request, "Akses ditolak!")
        return redirect("daftar_order")

    if request.method == "POST":
        new_status = request.POST.get("payment_status")
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")
            cursor.execute(
                'UPDATE "ORDER" SET payment_status = %s WHERE order_id = %s',
                [new_status, order_id],
            )
        messages.success(request, f"Status Order {order_id} berhasil diperbarui!")

    return redirect("daftar_order")


def delete_order(request, order_id):
    if SIMULASI_ROLE != "Admin":
        messages.error(request, "Akses ditolak!")
        return redirect("daftar_order")

    if request.method == "POST":
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")
            cursor.execute('DELETE FROM "ORDER" WHERE order_id = %s', [order_id])
        messages.success(request, f"Data Order {order_id} berhasil dihapus!")

    return redirect("daftar_order")


def promotion_list_view(request):
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute("""
            SELECT promotion_id, promo_code, discount_type, discount_value, start_date, end_date, usage_limit 
            FROM PROMOTION ORDER BY start_date DESC
        """)
        promotions = [
            {
                "promotion_id": row[0],
                "promo_code": row[1],
                "discount_type": row[2],
                "discount_value": row[3],
                "start_date": row[4],
                "end_date": row[5],
                "usage_limit": row[6],
            }
            for row in cursor.fetchall()
        ]

    context = {
        "promotions": promotions,
        "user_role": SIMULASI_ROLE,
    }
    return render(request, "promotion/promotion_list.html", context)


def create_promotion(request):
    if SIMULASI_ROLE != "Admin":
        messages.error(request, "Akses ditolak!")
        return redirect("promotion_list")

    if request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    INSERT INTO PROMOTION (promo_code, discount_type, discount_value, start_date, end_date, usage_limit)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    [
                        request.POST.get("promo_code").upper(),
                        request.POST.get("discount_type"),
                        request.POST.get("discount_value"),
                        request.POST.get("start_date"),
                        request.POST.get("end_date"),
                        request.POST.get("usage_limit"),
                    ],
                )
            messages.success(request, "Promo baru berhasil dibuat!")
        except Exception as e:
            messages.error(request, f"Gagal membuat promo: {e}")

    return redirect("promotion_list")


def update_promotion(request, promo_id):
    if SIMULASI_ROLE != "Admin":
        messages.error(request, "Akses ditolak!")
        return redirect("promotion_list")

    if request.method == "POST":
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    UPDATE PROMOTION 
                    SET promo_code = %s, discount_type = %s, discount_value = %s, 
                        start_date = %s, end_date = %s, usage_limit = %s
                    WHERE promotion_id = %s
                """,
                    [
                        request.POST.get("promo_code").upper(),
                        request.POST.get("discount_type"),
                        request.POST.get("discount_value"),
                        request.POST.get("start_date"),
                        request.POST.get("end_date"),
                        request.POST.get("usage_limit"),
                        promo_id,
                    ],
                )
            messages.success(request, "Data promo berhasil diperbarui!")
        except Exception as e:
            messages.error(request, f"Gagal update promo: {e}")

    return redirect("promotion_list")


def delete_promotion(request, promo_id):
    if SIMULASI_ROLE != "Admin":
        messages.error(request, "Akses ditolak!")
        return redirect("promotion_list")

    if request.method == "POST":
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")
            cursor.execute("DELETE FROM PROMOTION WHERE promotion_id = %s", [promo_id])
        messages.success(request, "Data promo berhasil dihapus!")

    return redirect("promotion_list")
