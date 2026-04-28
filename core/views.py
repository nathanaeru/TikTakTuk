from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.contrib import messages
import uuid, json
from .models import Venue, Seat, HasRelationship


def home_view(request):
    return redirect("dashboard")


def artist_list_view(request):
    # Mengarah ke templates/artist/artist.html
    return render(request, "artist/artist.html")


def ticket_category_list_view(request):
    # Mengarah ke templates/ticket/ticket-category.html sesuai nama file Anda
    return render(request, "ticket/ticket-category.html")


def dashboard_pengguna(request, page="main"):
    # USER GUEST
    user_id = request.session.get("user_id")

    if not user_id:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO tiktaktuk, public")
            cursor.execute(
                """
                SELECT e.event_title, e.event_datetime, v.venue_name 
                FROM EVENT e 
                JOIN VENUE v ON e.venue_id = v.venue_id 
                LIMIT 3
            """
            )
            trending_events = cursor.fetchall()

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

    # USER LOGIN
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO tiktaktuk, public")

        # UPDATE PROFIL (POST)
        if request.method == "POST" and page == "profile":
            nama_baru = request.POST.get("nama_lengkap")
            telp_baru = request.POST.get("nomor_telepon")

            # Cek role usernya
            cursor.execute(
                "SELECT role_id FROM account_role WHERE user_id = %s", [user_id]
            )
            # update logic

            cursor.execute(
                """
                UPDATE customer SET full_name = %s, phone_number = %s WHERE user_id = %s
            """,
                [nama_baru, telp_baru, user_id],
            )

            messages.success(request, "Profil Anda berhasil diperbarui!")
            return redirect("dashboard_page", page="profile")

        cursor.execute(
            """
            SELECT 
                u.username, 
                c.full_name, 
                c.phone_number, 
                org.organizer_name,
                c.customer_id,
                u.user_id
            FROM user_account u
            LEFT JOIN customer c ON u.user_id = c.user_id
            LEFT JOIN organizer org ON u.user_id = org.user_id
            WHERE u.user_id = %s
        """,
            [user_id],
        )

        user_data = cursor.fetchone()
        if not user_data:
            return render(request, "error.html", {"message": "User tidak ditemukan"})

        username, full_name, phone_number, organizer_name, cust_id, uid = user_data

        # CEK ROLE
        cursor.execute(
            """
            SELECT r.role_name FROM account_role ar
            JOIN role r ON ar.role_id = r.role_id
            WHERE ar.user_id = %s
        """,
            [user_id],
        )

        role_fetch = cursor.fetchone()
        raw_role_name = role_fetch[0].lower() if role_fetch else "customer"

        # Mapping Role Display
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

        # ======================== VIEW: PROFIL ========================
        if page == "profile":
            display_name = (
                organizer_name
                if role_display == "organizer"
                else (full_name or username)
            )
            context.update(
                {
                    "nama_lengkap": display_name,
                    "nomor_telepon": phone_number or "-",
                    "role_display": raw_role_name.capitalize(),
                }
            )
            return render(request, "dashboard/profile.html", context)

        # ======================== VIEW: DASHBOARD ========================
        if role_display == "customer":
            # Statistik Dashboard Customer
            cursor.execute(
                """
                SELECT COUNT(t.ticket_id) FROM TICKET t
                JOIN "ORDER" o ON t.torder_id = o.order_id
                JOIN TICKET_CATEGORY tc ON t.tcategory_id = tc.category_id
                JOIN EVENT e ON tc.tevent_id = e.event_id
                WHERE o.customer_id = %s AND e.event_datetime >= CURRENT_TIMESTAMP
            """,
                [cust_id],
            )
            tiket_aktif = cursor.fetchone()[0]

            cursor.execute(
                'SELECT COUNT(DISTINCT order_id) FROM "ORDER" WHERE customer_id = %s',
                [cust_id],
            )
            total_acara = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM PROMOTION WHERE end_date >= CURRENT_DATE"
            )
            kode_promo = cursor.fetchone()[0]

            cursor.execute(
                'SELECT COALESCE(SUM(total_amount), 0) FROM "ORDER" WHERE customer_id = %s',
                [cust_id],
            )
            belanja = float(cursor.fetchone()[0])
            belanja_display = (
                f"Rp {belanja / 1000000:.1f}M"
                if belanja >= 1000000
                else f"Rp {int(belanja/1000)}K"
            )

            # List Tiket
            cursor.execute(
                """
                SELECT e.event_title, e.event_datetime, v.venue_name, tc.category_name
                FROM TICKET t
                JOIN "ORDER" o ON t.torder_id = o.order_id
                JOIN TICKET_CATEGORY tc ON t.tcategory_id = tc.category_id
                JOIN EVENT e ON tc.tevent_id = e.event_id
                JOIN VENUE v ON e.venue_id = v.venue_id
                WHERE o.customer_id = %s AND e.event_datetime >= CURRENT_TIMESTAMP
                ORDER BY e.event_datetime ASC LIMIT 2
            """,
                [cust_id],
            )
            tiket_list = cursor.fetchall()

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

        else:  # ROLE ORGANIZER
            cursor.execute(
                "SELECT COUNT(*) FROM EVENT WHERE organizer_id = (SELECT organizer_id FROM organizer WHERE user_id = %s)",
                [user_id],
            )
            count_event = cursor.fetchone()[0]

            context.update(
                {"nama": organizer_name or username, "count_event": count_event}
            )

    return render(request, f"dashboard/{role_display}.html", context)


def get_role(user_id):
    if not user_id:
        return "guest"
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO tiktaktuk, public")
        cursor.execute(
            """
            SELECT r.role_name 
            FROM ACCOUNT_ROLE ar
            JOIN ROLE r ON ar.role_id = r.role_id
            WHERE ar.user_id = %s
            LIMIT 1
        """,
            [user_id],
        )
        res = cursor.fetchone()
        return res[0].lower() if res else "guest"


def ticket_list(request):
    user_id = request.session.get("user_id")
    # Identifikasi Role
    role = get_role(user_id)
    user_display_name = "Guest"

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO tiktaktuk, public")

        # condition berdasarkan Role
        if user_id:
            if role == "customer":
                cursor.execute(
                    "SELECT full_name FROM CUSTOMER WHERE user_id = %s", [user_id]
                )
                row = cursor.fetchone()
                user_display_name = row[0] if row else "Pelanggan"
            elif role == "organizer":
                cursor.execute(
                    "SELECT organizer_name FROM ORGANIZER WHERE user_id = %s", [user_id]
                )
                row = cursor.fetchone()
                user_display_name = row[0] if row else "Organizer"
            elif role == "administrator":
                cursor.execute(
                    "SELECT username FROM USER_ACCOUNT WHERE user_id = %s", [user_id]
                )
                row = cursor.fetchone()
                user_display_name = row[0] if row else "Admin"

        # 3. Read
        query_tickets = """
            SELECT 
                t.ticket_id, t.ticket_code, cust.full_name, e.event_title, 
                tc.category_name, tc.price, v.venue_name, v.city, e.event_datetime,
                o.order_id
            FROM TICKET t
            JOIN "ORDER" o ON t.torder_id = o.order_id
            JOIN CUSTOMER cust ON o.customer_id = cust.customer_id
            JOIN TICKET_CATEGORY tc ON t.tcategory_id = tc.category_id
            JOIN EVENT e ON tc.tevent_id = e.event_id
            JOIN VENUE v ON e.venue_id = v.venue_id
        """

        params = []
        # FILTER ROLE
        if role == "customer":
            query_tickets += " WHERE cust.user_id = %s"
            params.append(user_id)

        query_tickets += " ORDER BY e.event_datetime DESC, t.ticket_code ASC"

        cursor.execute(query_tickets, params)
        tickets = cursor.fetchall()

        # Statistik untuk Dashboard
        total_tiket = len(tickets)
        valid_count = total_tiket  # Bisa ditambah logic WHERE status='VALID'
        terpakai_count = 0

    # Modal Create (Admin/Organizer)
    orders_json, categories_json, seats_json = [], [], []

    if role in ["administrator", "organizer"]:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO tiktaktuk, public")

            # ata Order yang sudah lunas untuk dropdown
            cursor.execute(
                """
                SELECT DISTINCT o.order_id, cust.full_name, e.event_title, e.event_id
                FROM "ORDER" o
                JOIN CUSTOMER cust ON o.customer_id = cust.customer_id
                JOIN TICKET_CATEGORY tc ON tc.tevent_id = (
                    SELECT tevent_id FROM TICKET_CATEGORY tc2 
                    JOIN TICKET t2 ON t2.tcategory_id = tc2.category_id 
                    WHERE t2.torder_id = o.order_id LIMIT 1
                )
                JOIN EVENT e ON tc.tevent_id = e.event_id
                WHERE o.payment_status = 'LUNAS'
            """
            )
            orders_json = [
                {
                    "id": str(o[0]),
                    "display": f"{o[0]} — {o[1]} — {o[2]}",
                    "event_id": str(o[3]),
                }
                for o in cursor.fetchall()
            ]

            # Kategori Tiket
            cursor.execute(
                """
                SELECT tc.category_id, tc.category_name, tc.price, tc.quota, tc.tevent_id,
                (SELECT COUNT(*) FROM TICKET WHERE tcategory_id = tc.category_id) as used
                FROM TICKET_CATEGORY tc
            """
            )
            categories_json = [
                {
                    "id": str(c[0]),
                    "name": c[1],
                    "price": float(c[2]),
                    "quota": c[3],
                    "used": c[5],
                    "event_id": str(c[4]),
                    "has_seat": True if "General" not in c[1] else False,
                    "display": f"{c[1]} — Rp {c[2]:,.0f} ({c[5]}/{c[3]})",
                }
                for c in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT seat_id, seat_number, row_number 
                FROM SEAT 
                ORDER BY row_number, seat_number
            """
            )
            seats_json = [
                {"id": str(s[0]), "display": f"Baris {s[2]} — Kursi {s[1]}"}
                for s in cursor.fetchall()
            ]

    # Kirim ke Template
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


def create_ticket(request, user_id):
    user_id = request.session.get("user_id")
    # Proses penyimpanan tiket baru ke database.
    if request.method == "POST":
        order_id = request.POST.get("order")
        category_id = request.POST.get("category")
        seat_id = request.POST.get("seat")

        # Auto-generate kode tiket
        ticket_code = f"TTK-{uuid.uuid4().hex[:8].upper()}"
        new_ticket_id = uuid.uuid4()

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO tiktaktuk, public")
                # Insert TICKET
                cursor.execute(
                    """
                    INSERT INTO TICKET (ticket_id, ticket_code, torder_id, tcategory_id)
                    VALUES (%s, %s, %s, %s)
                """,
                    [new_ticket_id, ticket_code, order_id, category_id],
                )

                # Insert HAS_RELATIONSHIP (jika ada kursi)
                if seat_id:
                    cursor.execute(
                        """
                        INSERT INTO HAS_RELATIONSHIP (ticket_id, seat_id)
                        VALUES (%s, %s)
                    """,
                        [new_ticket_id, seat_id],
                    )

            messages.success(request, f"Tiket {ticket_code} berhasil dibuat!")
        except Exception as e:
            messages.error(request, f"Gagal membuat tiket: {e}")

    return redirect("ticket_list")


def update_ticket(request, ticket_id):
    user_id = request.session.get("user_id")
    if request.method == "POST":
        status = request.POST.get("status")
        seat_id = request.POST.get("seat")  # Bisa None/Kosong

        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO tiktaktuk, public")
            # Update status di tabel TICKET (asumsi ada kolom status)
            # Dan update seat_id (asumsi kolom seat_id ada di TICKET atau tabel relasi)
            cursor.execute(
                """
                UPDATE TICKET 
                SET status = %s, seat_id = %s 
                WHERE ticket_id = %s
            """,
                [status, seat_id if seat_id else None, ticket_id],
            )

    return redirect(request.META.get("HTTP_REFERER", "/"))


def delete_ticket(request, ticket_id):
    user_id = request.session.get("user_id")
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO tiktaktuk, public")
        # 1. Hapus relasi kursi dulu (jika ada tabel HAS_RELATIONSHIP)
        # cursor.execute('DELETE FROM HAS_RELATIONSHIP WHERE ticket_id = %s', [ticket_id])

        # 2. Hapus tiket secara permanen
        cursor.execute("DELETE FROM TICKET WHERE ticket_id = %s", [ticket_id])

    return redirect(request.META.get("HTTP_REFERER", "/"))


def seat_management(request):
    """
    Halaman List Kursi: Bisa dibaca semua role (Guest, Customer, Organizer, Admin).
    Aksi CUD: Hanya muncul untuk Admin & Organizer.
    """
    # Identifikasi Role
    user_id = request.session.get("user_id")
    raw_role = get_role(user_id)

    # Mapping Role
    if raw_role == "administrator":
        role_display = "admin"
    elif raw_role == "organizer":
        role_display = "organizer"
    elif raw_role == "customer":
        role_display = "customer"
    else:
        role_display = "guest"

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO tiktaktuk, public")

        # Nama User untuk Greeting
        user_display_name = "Guest"
        if user_id:
            if role_display == "organizer":
                cursor.execute(
                    "SELECT organizer_name FROM ORGANIZER WHERE user_id = %s", [user_id]
                )
            elif role_display == "customer":
                cursor.execute(
                    "SELECT full_name FROM CUSTOMER WHERE user_id = %s", [user_id]
                )
            else:
                cursor.execute(
                    "SELECT username FROM USER_ACCOUNT WHERE user_id = %s", [user_id]
                )

            row_name = cursor.fetchone()
            user_display_name = row_name[0] if row_name else "User"

        # read
        cursor.execute(
            """
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
        """
        )
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
        "venues_data": json.dumps(venues_json),
        "user_id": user_id,
        "user_name": user_display_name,
        "role": role_display,
        "title": "Seat Inventory",
    }

    return render(request, "dashboard/seat.html", context)


def create_seat(request):
    user_id = request.session.get("user_id")
    if request.method == "POST":
        venue_id = request.POST.get("venue")
        section = request.POST.get("section")
        row = request.POST.get("row")
        seat_num = request.POST.get("seat_number")
        new_id = uuid.uuid4()

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO tiktaktuk, public")
                cursor.execute(
                    """
                    INSERT INTO SEAT (seat_id, venue_id, section, row_number, seat_number)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    [new_id, venue_id, section, row, seat_num],
                )
            messages.success(request, "Kursi baru berhasil muncul di tabel!")
        except Exception as e:
            messages.error(
                request, "Gagal! Kombinasi kursi di venue tersebut sudah ada."
            )

    return redirect("seat_management", user_id=user_id)


def update_seat(request, seat_id):
    user_id = request.session.get("user_id")
    if request.method == "POST":
        venue_id = request.POST.get("venue")
        section = request.POST.get("section")
        row = request.POST.get("row")
        seat_num = request.POST.get("seat_number")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO tiktaktuk, public")
                cursor.execute(
                    """
                    UPDATE SEAT 
                    SET venue_id = %s, section = %s, row_number = %s, seat_number = %s
                    WHERE seat_id = %s
                """,
                    [venue_id, section, row, seat_num, seat_id],
                )
            messages.success(request, "Perubahan diterapkan pada tabel!")
        except Exception:
            messages.error(request, "Gagal update! Data mungkin duplikat.")

    return redirect("seat_management", user_id=user_id)


def delete_seat(request, seat_id):
    user_id = request.session.get("user_id")
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
