import json
import uuid
from datetime import datetime

from django.contrib import messages
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.shortcuts import redirect, render
from django.utils import timezone


def home_view(request):
    return redirect("dashboard")


def fetch_all_dict(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_one_dict(cursor):
    row = cursor.fetchone()
    if not row:
        return None
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row))


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
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute(
            """
            SELECT LOWER(r.role_name)
            FROM ACCOUNT_ROLE ar
            JOIN ROLE r ON r.role_id = ar.role_id
            WHERE ar.user_id = %s
            ORDER BY CASE
                WHEN LOWER(r.role_name) = 'administrator' THEN 1
                WHEN LOWER(r.role_name) = 'organizer' THEN 2
                WHEN LOWER(r.role_name) = 'customer' THEN 3
                ELSE 4
            END
            LIMIT 1
        """,
            [user_id],
        )
        row = cursor.fetchone()
        return row[0] if row else "guest"


def dashboard_pengguna(request, page="main"):
    user_id = request.session.get("user_id")

    # ======================== USER GUEST ========================
    if not user_id:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")
            cursor.execute("""
                SELECT e.event_title, e.event_datetime, v.venue_name
                FROM EVENT e
                JOIN VENUE v ON v.venue_id = e.venue_id
                ORDER BY e.event_datetime ASC
                LIMIT 3
            """)
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

    # ======================== USER LOGIN ========================
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute(
            "SELECT user_id, username FROM USER_ACCOUNT WHERE user_id = %s",
            [user_id],
        )
        user_row = cursor.fetchone()

        if not user_row:
            messages.error(request, "Akun tidak ditemukan.")
            return redirect("auth:login")

        cursor.execute(
            "SELECT customer_id, full_name, phone_number FROM CUSTOMER WHERE user_id = %s",
            [user_id],
        )
        customer_row = cursor.fetchone()

        cursor.execute(
            "SELECT organizer_id, organizer_name, contact_email FROM ORGANIZER WHERE user_id = %s",
            [user_id],
        )
        organizer_row = cursor.fetchone()

    customer = None
    if customer_row:
        customer = {
            "customer_id": str(customer_row[0]),
            "full_name": customer_row[1],
            "phone_number": customer_row[2],
        }

    organizer = None
    if organizer_row:
        organizer = {
            "organizer_id": str(organizer_row[0]),
            "organizer_name": organizer_row[1],
            "contact_email": organizer_row[2],
        }

    if request.method == "POST" and page == "profile":
        nama_baru = request.POST.get("nama_lengkap")
        telp_baru = request.POST.get("nomor_telepon")

        if customer:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    UPDATE CUSTOMER
                    SET full_name = %s, phone_number = %s
                    WHERE user_id = %s
                """,
                    [nama_baru, telp_baru, user_id],
                )
        elif organizer:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    UPDATE ORGANIZER
                    SET organizer_name = %s
                    WHERE user_id = %s
                """,
                    [nama_baru, user_id],
                )

        messages.success(request, "Profil Anda berhasil diperbarui!")
        return redirect("dashboard_page", page="profile")

    username = user_row[1]
    full_name = customer["full_name"] if customer else None
    phone_number = customer["phone_number"] if customer else None
    organizer_name = organizer["organizer_name"] if organizer else None

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
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM TICKET t
                    JOIN "ORDER" o ON o.order_id = t.torder_id
                    JOIN TICKET_CATEGORY tc ON tc.category_id = t.tcategory_id
                    JOIN EVENT e ON e.event_id = tc.tevent_id
                    WHERE o.customer_id = %s
                      AND e.event_datetime >= %s
                """,
                    [customer["customer_id"], timezone.now()],
                )
                tiket_aktif = cursor.fetchone()[0] or 0

                cursor.execute(
                    'SELECT COUNT(DISTINCT order_id) FROM "ORDER" WHERE customer_id = %s',
                    [customer["customer_id"]],
                )
                total_acara = cursor.fetchone()[0] or 0

                cursor.execute(
                    "SELECT COUNT(*) FROM PROMOTION WHERE end_date >= CURRENT_DATE"
                )
                kode_promo = cursor.fetchone()[0] or 0

                cursor.execute(
                    'SELECT COALESCE(SUM(total_amount), 0) FROM "ORDER" WHERE customer_id = %s',
                    [customer["customer_id"]],
                )
                belanja = cursor.fetchone()[0] or 0.0

            belanja_display = (
                f"Rp {belanja / 1000000:.1f}M"
                if belanja >= 1000000
                else f"Rp {int(belanja/1000)}K"
            )

            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    SELECT e.event_title, e.event_datetime, v.venue_name, tc.category_name
                    FROM TICKET t
                    JOIN "ORDER" o ON o.order_id = t.torder_id
                    JOIN TICKET_CATEGORY tc ON tc.category_id = t.tcategory_id
                    JOIN EVENT e ON e.event_id = tc.tevent_id
                    JOIN VENUE v ON v.venue_id = e.venue_id
                    WHERE o.customer_id = %s
                      AND e.event_datetime >= %s
                    ORDER BY e.event_datetime ASC
                    LIMIT 2
                """,
                    [customer["customer_id"], timezone.now()],
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

    else:
        if organizer:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    "SELECT COUNT(*) FROM EVENT WHERE organizer_id = %s",
                    [organizer["organizer_id"]],
                )
                count_event = cursor.fetchone()[0] or 0
            context.update(
                {"nama": organizer_name or username, "count_event": count_event}
            )

    return render(request, f"dashboard/{role_display}.html", context)


def ticket_list(request, user_id=None):
    user_id = user_id or request.session.get("user_id")
    role = get_role(user_id)
    user_display_name = "Guest"

    if user_id:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")
            if role == "customer":
                cursor.execute(
                    "SELECT full_name FROM CUSTOMER WHERE user_id = %s", [user_id]
                )
            elif role == "organizer":
                cursor.execute(
                    "SELECT organizer_name FROM ORGANIZER WHERE user_id = %s", [user_id]
                )
            else:
                cursor.execute(
                    "SELECT username FROM USER_ACCOUNT WHERE user_id = %s", [user_id]
                )
            name_row = cursor.fetchone()
            user_display_name = name_row[0] if name_row else "User"

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'ticket' AND column_name = 'status'
                  AND table_schema IN ('tiktaktuk', 'TikTakTuk', 'public')
            )
            """
        )
        has_status = cursor.fetchone()[0]

    status_select = (
        "COALESCE(t.status, 'VALID') AS status" if has_status else "'VALID' AS status"
    )

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        ticket_sql = (
            "SELECT\n"
            "    t.ticket_id,\n"
            "    t.ticket_code,\n"
            "    c.full_name AS customer_name,\n"
            "    e.event_title,\n"
            "    tc.category_name,\n"
            "    tc.price,\n"
            "    v.venue_name,\n"
            "    v.city,\n"
            "    e.event_datetime,\n"
            "    t.torder_id,\n"
            f"    {status_select}\n"
            "FROM TICKET t\n"
            'JOIN "ORDER" o ON o.order_id = t.torder_id\n'
            "JOIN CUSTOMER c ON c.customer_id = o.customer_id\n"
            "JOIN TICKET_CATEGORY tc ON tc.category_id = t.tcategory_id\n"
            "JOIN EVENT e ON e.event_id = tc.tevent_id\n"
            "JOIN VENUE v ON v.venue_id = e.venue_id\n"
        )
        params = []
        if role == "customer":
            ticket_sql += " WHERE c.user_id = %s"
            params.append(user_id)
        ticket_sql += " ORDER BY e.event_datetime DESC, t.ticket_code"
        cursor.execute(ticket_sql, params)
        ticket_rows = fetch_all_dict(cursor)

    tickets = []
    valid_count = 0
    terpakai_count = 0

    for row in ticket_rows:
        status_db = (row["status"] or "VALID").strip().upper()
        if status_db == "TERPAKAI":
            terpakai_count += 1
            status_display = "TERPAKAI"
        elif status_db == "VOID":
            status_display = "VOID"
        else:
            valid_count += 1
            status_display = "VALID"

        tickets.append((
            str(row["ticket_id"]),
            row["ticket_code"],
            row["customer_name"],
            row["event_title"],
            row["category_name"],
            row["price"],
            row["venue_name"],
            row["city"],
            row["event_datetime"],
            str(row["torder_id"]),
            status_display,
        ))

    orders_json = []
    categories_json = []
    seats_json = []

    if role in ["administrator", "organizer"]:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")
            cursor.execute("""
                SELECT DISTINCT ON (o.order_id)
                    o.order_id,
                    c.full_name,
                    e.event_id,
                    e.event_title
                FROM "ORDER" o
                JOIN CUSTOMER c ON c.customer_id = o.customer_id
                JOIN TICKET t ON t.torder_id = o.order_id
                JOIN TICKET_CATEGORY tc ON tc.category_id = t.tcategory_id
                JOIN EVENT e ON e.event_id = tc.tevent_id
                WHERE o.payment_status = 'LUNAS'
                ORDER BY o.order_id, e.event_datetime ASC
            """)
            order_rows = fetch_all_dict(cursor)
            orders_json = [
                {
                    "id": str(row["order_id"]),
                    "display": f"{str(row['order_id'])[:8]} — {row['full_name']} — {row['event_title']}",
                    "event_id": str(row["event_id"]),
                }
                for row in order_rows
            ]

            cursor.execute("""
                SELECT
                    tc.category_id,
                    tc.category_name,
                    tc.price,
                    tc.quota,
                    tc.tevent_id,
                    v.jenis_seating,
                    COUNT(t.ticket_id) AS used
                FROM TICKET_CATEGORY tc
                JOIN EVENT e ON e.event_id = tc.tevent_id
                JOIN VENUE v ON v.venue_id = e.venue_id
                LEFT JOIN TICKET t ON t.tcategory_id = tc.category_id
                GROUP BY tc.category_id, tc.category_name, tc.price, tc.quota,
                         tc.tevent_id, v.jenis_seating
                ORDER BY tc.category_name
            """)
            category_rows = fetch_all_dict(cursor)
            categories_json = [
                {
                    "id": str(row["category_id"]),
                    "display": f"{row['category_name']} — Rp {int(row['price']):,} — ({row['used']}/{row['quota']})",
                    "event_id": str(row["tevent_id"]),
                    "quota": row["quota"],
                    "used": row["used"],
                    "has_seat": row["jenis_seating"] == "Reserved Seating",
                }
                for row in category_rows
            ]

            cursor.execute("""
                SELECT s.seat_id, s.section, s.row_number, s.seat_number, s.venue_id
                FROM SEAT s
                LEFT JOIN HAS_RELATIONSHIP hr ON hr.seat_id = s.seat_id
                WHERE hr.seat_id IS NULL
                ORDER BY s.section, s.row_number, s.seat_number
            """)
            seat_rows = fetch_all_dict(cursor)
            seats_json = [
                {
                    "id": str(row["seat_id"]),
                    "display": f"{row['section']} — Baris {row['row_number']}, No. {row['seat_number']}",
                    "venue_id": str(row["venue_id"]),
                }
                for row in seat_rows
            ]

    context = {
        "tickets":        tickets,
        "total_tiket":    len(tickets),
        "valid_count":    valid_count,
        "terpakai_count": terpakai_count,
        "orders_data":    json.dumps(orders_json),
        "categories_data":json.dumps(categories_json),
        "seats_data":     json.dumps(seats_json),
        "user_id":        user_id,
        "user_name":      user_display_name,
        "role":           role,
        "title": (
            "Manajemen Tiket" if role in ["administrator", "organizer"] else "Tiket Saya"
        ),
    }
    return render(request, "ticket/ticket_list.html", context)

def create_ticket(request, user_id):
    """
    Buat tiket baru.
    Validasi:
      1. Duplikat — tiket dengan order + kategori yang sama sudah ada.
      2. Kursi sudah terisi (jika dipilih).
      3. Kuota penuh — ditangkap dari trigger DB (trg_check_ticket_quota).
    """
    if request.method != "POST":
        return redirect("ticket_list", user_id=user_id)

    role = get_current_role(request)
    if role not in ["admin", "organizer"]:
        messages.error(
            request,
            "Akses Ditolak! Hanya Admin atau Organizer yang dapat membuat tiket.",
        )
        return redirect("ticket_list", user_id=user_id)

    order_id    = request.POST.get("order")
    category_id = request.POST.get("category")
    seat_id     = request.POST.get("seat")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")

            # 1. Cek duplikat tiket (order + kategori sama)
            cursor.execute(
                """
                SELECT ticket_code
                FROM TICKET
                WHERE torder_id = %s AND tcategory_id = %s
                LIMIT 1
                """,
                [order_id, category_id],
            )
            duplicate = cursor.fetchone()
            if duplicate:
                messages.error(
                    request,
                    f"ERROR: Tiket untuk order dan kategori ini sudah ada "
                    f"(kode: {duplicate[0]}). Tidak dapat membuat tiket duplikat.",
                )
                return redirect("ticket_list", user_id=user_id)

            # 2. Cek kursi sudah terisi
            if seat_id and seat_id != "tanpa_kursi":
                cursor.execute(
                    "SELECT 1 FROM HAS_RELATIONSHIP WHERE seat_id = %s LIMIT 1",
                    [seat_id],
                )
                if cursor.fetchone():
                    messages.error(
                        request,
                        "ERROR: Kursi yang dipilih sudah terisi. Pilih kursi lain.",
                    )
                    return redirect("ticket_list", user_id=user_id)

            # 3. Insert — trigger DB akan cek kuota, exception ditangkap di bawah
            ticket_code   = f"TTK-{uuid.uuid4().hex[:8].upper()}"
            new_ticket_id = uuid.uuid4()

            cursor.execute(
                """
                INSERT INTO TICKET (ticket_id, ticket_code, torder_id, tcategory_id)
                VALUES (%s, %s, %s, %s)
                """,
                [str(new_ticket_id), ticket_code, order_id, category_id],
            )

            # 4. Assign kursi bila dipilih
            if seat_id and seat_id != "tanpa_kursi":
                cursor.execute(
                    "INSERT INTO HAS_RELATIONSHIP (ticket_id, seat_id) VALUES (%s, %s)",
                    [str(new_ticket_id), seat_id],
                )

        messages.success(request, f"Tiket {ticket_code} berhasil dibuat!")

    except Exception as e:
        # Tangkap pesan dari trigger kuota atau error DB lainnya
        messages.error(request, f"ERROR: {clean_db_error(e)}")

    return redirect("ticket_list", user_id=user_id)


def update_ticket(request, user_id, ticket_id):
    """
    Update status dan/atau kursi tiket.
    Validasi:
      - Kursi baru yang dipilih belum dipakai tiket LAIN.
    """
    if request.method != "POST":
        return redirect("ticket_list", user_id=user_id)

    raw_role = get_current_role(request)
    role = str(raw_role).strip().lower() if raw_role else ""

    if role not in ["administrator", "admin", "organizer"]:
        messages.error(request, "Akses Ditolak!")
        return redirect("ticket_list", user_id=user_id)

    new_status = request.POST.get("status", "VALID").upper()
    seat_id    = request.POST.get("seat")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")

            # Cek kursi baru tidak dipakai tiket LAIN
            if seat_id and seat_id != "tanpa_kursi":
                cursor.execute(
                    """
                    SELECT hr.ticket_id
                    FROM HAS_RELATIONSHIP hr
                    WHERE hr.seat_id = %s AND hr.ticket_id <> %s
                    LIMIT 1
                    """,
                    [seat_id, ticket_id],
                )
                if cursor.fetchone():
                    messages.error(
                        request,
                        "ERROR: Kursi yang dipilih sudah dipakai oleh tiket lain. "
                        "Pilih kursi lain atau biarkan tanpa kursi.",
                    )
                    return redirect("ticket_list", user_id=user_id)

            # Update status jika kolom ada
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'ticket' AND column_name = 'status'
                      AND table_schema IN ('tiktaktuk', 'TikTakTuk', 'public')
                )
                """
            )
            has_status = cursor.fetchone()[0]

            if has_status:
                cursor.execute(
                    "UPDATE TICKET SET status = %s WHERE ticket_id = %s",
                    [new_status, ticket_id],
                )

            # Update relasi kursi
            cursor.execute(
                "DELETE FROM HAS_RELATIONSHIP WHERE ticket_id = %s", [ticket_id]
            )
            if seat_id and seat_id != "tanpa_kursi":
                cursor.execute(
                    "INSERT INTO HAS_RELATIONSHIP (ticket_id, seat_id) VALUES (%s, %s)",
                    [ticket_id, seat_id],
                )

        messages.success(request, "Data tiket berhasil diperbarui!")

    except Exception as e:
        messages.error(request, f"ERROR: {clean_db_error(e)}")

    return redirect("ticket_list", user_id=user_id)

def delete_ticket(request, user_id, ticket_id):
    """Hapus tiket — hanya Admin."""
    role = get_current_role(request)
    if role != "admin":
        messages.error(
            request, "Akses Ditolak! Hanya Admin yang dapat menghapus tiket."
        )
        return redirect("ticket_list", user_id=user_id)

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO tiktaktuk, public")
            cursor.execute(
                "DELETE FROM HAS_RELATIONSHIP WHERE ticket_id = %s", [ticket_id]
            )
            cursor.execute("DELETE FROM TICKET WHERE ticket_id = %s", [ticket_id])

        messages.success(request, "Tiket berhasil dihapus.")

    except Exception as e:
        messages.error(request, f"ERROR: {clean_db_error(e)}")

    return redirect("ticket_list", user_id=user_id)


def seat_management(request, user_id=None):
    current_user_id = user_id or request.session.get("user_id")
    raw_role = get_role(current_user_id)

    role_map = {
        "administrator": "admin",
        "organizer": "organizer",
        "customer": "customer",
    }
    role_display = role_map.get(raw_role, "guest")

    seat_base_path = (
        f"/dashboard/{current_user_id}/seat" if current_user_id else "/dashboard/seat"
    )

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO tiktaktuk, public")

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

        cursor.execute("""
            SELECT
                s.seat_id, s.section, s.row_number, s.seat_number, v.venue_name,
                CASE
                    WHEN hr.seat_id IS NOT NULL THEN 'TERISI'
                    ELSE 'TERSEDIA'
                END AS status,
                v.venue_id
            FROM SEAT s
            JOIN VENUE v ON s.venue_id = v.venue_id
            LEFT JOIN HAS_RELATIONSHIP hr ON s.seat_id = hr.seat_id
            ORDER BY v.venue_name, s.section, s.row_number, s.seat_number
        """)
        seat_list = [
            {
                "seat_id": str(r[0]),
                "section": r[1],
                "row":     r[2],
                "number":  r[3],
                "venue":   r[4],
                "status":  r[5],
                "venue_id":str(r[6]),
            }
            for r in cursor.fetchall()
        ]

        cursor.execute("SELECT COUNT(*) FROM SEAT")
        total_seats = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM HAS_RELATIONSHIP")
        total_taken = cursor.fetchone()[0] or 0

        venues_json = []
        if role_display in ["admin", "organizer"]:
            cursor.execute("SELECT venue_id, venue_name FROM VENUE")
            venues_json = [{"id": str(v[0]), "nama": v[1]} for v in cursor.fetchall()]

    context = {
        "seats":               seat_list,
        "total_kursi":         total_seats,
        "total_terisi":        total_taken,
        "total_tersedia":      total_seats - total_taken,
        "seat_create_url":     f"{seat_base_path}/create/",
        "seat_update_base_url":f"{seat_base_path}/update/",
        "seat_delete_base_url":f"{seat_base_path}/delete/",
        "venues_data":         json.dumps(venues_json),
        "user_id":             str(current_user_id) if current_user_id else "",
        "user_name":           user_display_name,
        "role":                role_display,
        "title":               "Seat Inventory",
    }
    return render(request, "dashboard/seat.html", context)

def create_seat(request, user_id):
    """
    Tambah kursi baru.
    Validasi:
      - No. kursi harus angka positif.
      - Kombinasi (venue, section, row_number, seat_number) harus UNIK.
    """
    if request.method != "POST":
        return redirect("seat_management", user_id=user_id)

    v_id  = request.POST.get("venue")
    sec   = request.POST.get("section")
    row   = request.POST.get("row")
    s_num = request.POST.get("seat_number")

    if not s_num or not s_num.isdigit() or int(s_num) < 1:
        messages.error(request, f"ERROR: No. kursi '{s_num}' tidak valid!")
        return redirect("seat_management", user_id=user_id)

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO tiktaktuk, public")

            # Cek duplikat
            cursor.execute(
                """
                SELECT s.seat_id
                FROM SEAT s
                WHERE s.venue_id = %s
                  AND LOWER(s.section) = LOWER(%s)
                  AND s.row_number = %s
                  AND s.seat_number = %s
                LIMIT 1
                """,
                [v_id, sec, row, s_num],
            )
            if cursor.fetchone():
                cursor.execute(
                    "SELECT venue_name FROM VENUE WHERE venue_id = %s", [v_id]
                )
                venue_row = cursor.fetchone()
                venue_name = venue_row[0] if venue_row else v_id
                messages.error(
                    request,
                    f"ERROR: Kursi {sec} - Baris {row} No. {s_num} di venue "
                    f'"{venue_name}" sudah tersedia. Tidak dapat menambah duplikat.',
                )
                return redirect("seat_management", user_id=user_id)

            cursor.execute(
                """
                INSERT INTO SEAT (venue_id, section, row_number, seat_number)
                VALUES (%s, %s, %s, %s)
                """,
                [v_id, sec, row, s_num],
            )

        messages.success(request, "Kursi berhasil ditambahkan!")

    except IntegrityError:
        messages.error(request, "ERROR: Gagal! Kombinasi kursi sudah ada di venue ini.")
    except Exception as e:
        messages.error(request, f"ERROR: {clean_db_error(e)}")

    return redirect("seat_management", user_id=user_id)

def update_seat(request, user_id, seat_id):
    """
    Update data kursi.
    Validasi:
      - No. kursi harus angka positif.
      - Kombinasi baru harus UNIK, kecuali milik seat_id sendiri.
    """
    if request.method != "POST":
        return redirect("seat_management", user_id=user_id)

    v_id  = request.POST.get("venue")
    sec   = request.POST.get("section")
    row   = request.POST.get("row")
    s_num = request.POST.get("seat_number")

    if not s_num or not s_num.isdigit() or int(s_num) < 1:
        messages.error(request, f"ERROR: No. kursi '{s_num}' tidak valid!")
        return redirect("seat_management", user_id=user_id)

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO tiktaktuk, public")

            # Cek duplikat, abaikan seat_id milik baris yang sedang diedit
            cursor.execute(
                """
                SELECT s.seat_id
                FROM SEAT s
                WHERE s.venue_id = %s
                  AND LOWER(s.section) = LOWER(%s)
                  AND s.row_number = %s
                  AND s.seat_number = %s
                  AND s.seat_id <> %s
                LIMIT 1
                """,
                [v_id, sec, row, s_num, seat_id],
            )
            if cursor.fetchone():
                cursor.execute(
                    "SELECT venue_name FROM VENUE WHERE venue_id = %s", [v_id]
                )
                venue_row = cursor.fetchone()
                venue_name = venue_row[0] if venue_row else v_id
                messages.error(
                    request,
                    f"ERROR: Kursi {sec} - Baris {row} No. {s_num} di venue "
                    f'"{venue_name}" sudah ada. Perubahan tidak dapat disimpan.',
                )
                return redirect("seat_management", user_id=user_id)

            cursor.execute(
                """
                UPDATE SEAT
                SET venue_id = %s, section = %s, row_number = %s, seat_number = %s
                WHERE seat_id = %s
                """,
                [v_id, sec, row, s_num, seat_id],
            )

        messages.success(request, "Perubahan berhasil disimpan!")

    except IntegrityError:
        messages.error(request, "ERROR: Gagal update! Data mungkin duplikat.")
    except Exception as e:
        messages.error(request, f"ERROR: {clean_db_error(e)}")

    return redirect("seat_management", user_id=user_id)

def delete_seat(request, user_id, seat_id):
    """
    Hapus kursi.
    Validasi (requirement no. 5):
      - Kursi yang sudah di-assign ke tiket (ada di HAS_RELATIONSHIP) TIDAK boleh dihapus.
      - Format pesan: "ERROR: Kursi <section> - Baris <row> No. <seat_number>
        tidak dapat dihapus karena sudah terisi."
      - Trigger DB (trg_check_seat_delete) juga menjaga ini di level database;
        pesannya ikut ditangkap jika lolos pengecekan app.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO tiktaktuk, public")

            # Ambil detail kursi untuk pesan yang informatif
            cursor.execute(
                "SELECT section, row_number, seat_number FROM SEAT WHERE seat_id = %s",
                [seat_id],
            )
            seat_row = cursor.fetchone()
            if not seat_row:
                messages.error(request, "ERROR: Kursi tidak ditemukan.")
                return redirect("seat_management", user_id=user_id)

            sec, row_num, seat_num = seat_row

            # Cek apakah kursi sudah di-assign ke tiket
            cursor.execute(
                "SELECT 1 FROM HAS_RELATIONSHIP WHERE seat_id = %s LIMIT 1",
                [seat_id],
            )
            if cursor.fetchone():
                messages.error(
                    request,
                    f"ERROR: Kursi {sec} - Baris {row_num} No. {seat_num} "
                    f"tidak dapat dihapus karena sudah terisi.",
                )
                return redirect("seat_management", user_id=user_id)

            cursor.execute("DELETE FROM SEAT WHERE seat_id = %s", [seat_id])

        messages.success(request, "Kursi berhasil dihapus.")

    except Exception as e:
        # Tangkap juga pesan dari trigger DB
        messages.error(request, f"ERROR: {clean_db_error(e)}")

    return redirect("seat_management", user_id=user_id)

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

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute("""
            SELECT venue_id, venue_name, address, city, capacity, jenis_seating
            FROM VENUE
            ORDER BY city, venue_name
        """)
        venues = [
            {
                "id": str(row[0]),
                "name": row[1],
                "address": row[2],
                "city": row[3],
                "capacity": row[4],
                "jenis_seating": row[5],
                "has_reserved_seating": row[5] == "Reserved Seating",
            }
            for row in cursor.fetchall()
        ]

        cursor.execute("SELECT COALESCE(SUM(capacity), 0) FROM VENUE")
        total_capacity = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT COUNT(*) FROM VENUE WHERE jenis_seating = 'Reserved Seating'"
        )
        reserved_count = cursor.fetchone()[0] or 0

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
        capacity = int(capacity)

        if capacity <= 0:
            messages.error(request, "Capacity harus lebih dari 0.")
            return redirect("venue_list")
        has_reserved = request.POST.get("has_reserved_seating") == "on"

        jenis_seating = "Reserved Seating" if has_reserved else "Free Seating"

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    SELECT venue_id
                    FROM VENUE
                    WHERE LOWER(venue_name) = LOWER(%s)
                      AND LOWER(city) = LOWER(%s)
                    LIMIT 1
                """,
                    [name, city],
                )
                duplicate = cursor.fetchone()

                if duplicate:
                    messages.error(
                        request,
                        f'ERROR: Venue "{name}" di kota "{city}" sudah terdaftar dengan ID {duplicate[0]}.',
                    )
                    return redirect("venue_list")

                cursor.execute(
                    """
                    INSERT INTO VENUE (venue_id, venue_name, capacity, address, city, jenis_seating)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    [uuid.uuid4(), name, capacity, address, city, jenis_seating],
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

    if request.method == "POST":
        name = request.POST.get("venue_name", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        capacity = request.POST.get("capacity")
        capacity = int(capacity)
        if capacity <= 0:
            messages.error(request, "Capacity harus lebih dari 0.")
            return redirect("venue_list")
        has_reserved = request.POST.get("has_reserved_seating") == "on"

        jenis_seating = "Reserved Seating" if has_reserved else "Free Seating"

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    SELECT venue_id
                    FROM VENUE
                    WHERE LOWER(venue_name) = LOWER(%s)
                      AND LOWER(city) = LOWER(%s)
                      AND venue_id <> %s
                    LIMIT 1
                """,
                    [name, city, venue_id],
                )
                duplicate = cursor.fetchone()

                if duplicate:
                    messages.error(
                        request,
                        f'ERROR: Venue "{name}" di kota "{city}" sudah terdaftar dengan ID {duplicate[0]}.',
                    )
                    return redirect("venue_list")

                cursor.execute(
                    """
                    UPDATE VENUE
                    SET venue_name = %s, address = %s, city = %s, capacity = %s, jenis_seating = %s
                    WHERE venue_id = %s
                """,
                    [name, address, city, capacity, jenis_seating, venue_id],
                )
            messages.success(request, "Venue berhasil diperbarui.")

        except DatabaseError as e:
            messages.error(request, clean_db_error(e))

        return redirect("venue_list")


def delete_venue(request, venue_id):
    role = get_current_role(request)
    if role not in ["admin", "organizer"]:
        messages.error(request, "Anda tidak memiliki akses untuk menghapus venue.")
        return redirect("venue_list")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")
            cursor.execute(
                "SELECT venue_name FROM VENUE WHERE venue_id = %s", [venue_id]
            )
            venue_row = cursor.fetchone()
            if not venue_row:
                messages.error(request, "Venue tidak ditemukan.")
                return redirect("venue_list")

            cursor.execute(
                """
                SELECT 1
                FROM EVENT
                WHERE venue_id = %s AND event_datetime >= %s
                LIMIT 1
            """,
                [venue_id, timezone.now()],
            )
            has_active_event = cursor.fetchone() is not None

            if has_active_event:
                messages.error(
                    request,
                    f'ERROR: Venue "{venue_row[0]}" masih memiliki event aktif sehingga tidak dapat dihapus.',
                )
                return redirect("venue_list")

            cursor.execute("DELETE FROM VENUE WHERE venue_id = %s", [venue_id])
        messages.success(request, "Venue berhasil dihapus.")

    except DatabaseError as e:
        messages.error(request, clean_db_error(e))
    return redirect("venue_list")


def fetch_event_artists(event_id):
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute(
            """
            SELECT a.artist_id, a.name, a.genre, ea.role
            FROM EVENT_ARTIST ea
            JOIN ARTIST a ON a.artist_id = ea.artist_id
            WHERE ea.event_id = %s
            ORDER BY a.name
        """,
            [event_id],
        )
        return fetch_all_dict(cursor)


def fetch_event_categories(event_id):
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute(
            """
            SELECT category_id, category_name, quota, price, tevent_id
            FROM TICKET_CATEGORY
            WHERE tevent_id = %s
            ORDER BY price DESC, category_name
        """,
            [event_id],
        )
        return fetch_all_dict(cursor)


def format_event(event_row):
    categories = fetch_event_categories(event_row["event_id"])
    artists = fetch_event_artists(event_row["event_id"])
    min_price = min([category["price"] for category in categories], default=0)

    return {
        "id": str(event_row["event_id"]),
        "title": event_row["event_title"],
        "date": event_row["event_datetime"].strftime("%Y-%m-%d"),
        "time": event_row["event_datetime"].strftime("%H:%M"),
        "venue": event_row["venue_name"],
        "venue_id": str(event_row["venue_id"]),
        "artists": [artist["name"] for artist in artists],
        "price": f"{min_price:,.0f}".replace(",", "."),
        "categories": [category["category_name"] for category in categories],
        "icon": "🎵",
        "organizer_id": str(event_row["organizer_id"]),
    }


def fetch_events(event_sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute(event_sql, params or [])
        return [format_event(row) for row in fetch_all_dict(cursor)]


def event_list(request):
    search = request.GET.get("search")
    venue_id = request.GET.get("venue")
    artist_id = request.GET.get("artist")

    event_sql = """
        SELECT DISTINCT e.event_id, e.event_datetime, e.event_title, e.venue_id, v.venue_name, e.organizer_id
        FROM EVENT e
        JOIN VENUE v ON v.venue_id = e.venue_id
    """
    filters = []
    params = []

    if artist_id:
        event_sql += " JOIN EVENT_ARTIST ea ON ea.event_id = e.event_id"
        filters.append("ea.artist_id = %s")
        params.append(artist_id)

    if search:
        filters.append("e.event_title ILIKE %s")
        params.append(f"%{search}%")

    if venue_id:
        filters.append("e.venue_id = %s")
        params.append(venue_id)

    if filters:
        event_sql += " WHERE " + " AND ".join(filters)

    event_sql += " ORDER BY e.event_datetime"

    events = fetch_events(event_sql, params)

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute(
            "SELECT venue_id, venue_name FROM VENUE ORDER BY city, venue_name"
        )
        venues = [
            {"venue_id": str(row[0]), "venue_name": row[1]} for row in cursor.fetchall()
        ]

        cursor.execute("SELECT artist_id, name FROM ARTIST ORDER BY name")
        artists = [
            {"artist_id": str(row[0]), "name": row[1]} for row in cursor.fetchall()
        ]

    return render(
        request,
        "event/event_list.html",
        {
            "role": get_current_role(request),
            "events": events,
            "venues": venues,
            "artists": artists,
        },
    )


def admin_event_list(request):
    events = fetch_events("""
        SELECT e.event_id, e.event_datetime, e.event_title, e.venue_id, v.venue_name, e.organizer_id
        FROM EVENT e
        JOIN VENUE v ON v.venue_id = e.venue_id
        ORDER BY e.event_datetime
    """)

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute(
            "SELECT venue_id, venue_name FROM VENUE ORDER BY city, venue_name"
        )
        venues = [
            {"venue_id": str(row[0]), "venue_name": row[1]} for row in cursor.fetchall()
        ]

        cursor.execute(
            "SELECT organizer_id, organizer_name FROM ORGANIZER ORDER BY organizer_name"
        )
        organizers = [
            {"organizer_id": str(row[0]), "organizer_name": row[1]}
            for row in cursor.fetchall()
        ]

        cursor.execute("SELECT artist_id, name FROM ARTIST ORDER BY name")
        artists = [
            {"artist_id": str(row[0]), "name": row[1]} for row in cursor.fetchall()
        ]

    return render(
        request,
        "event/my_event_list.html",
        {
            "role": "admin",
            "events": events,
            "venues": venues,
            "organizers": organizers,
            "artists": artists,
        },
    )


def my_event_list(request):
    user_id = request.session.get("user_id")
    role = get_current_role(request)

    if role != "organizer":
        messages.error(
            request, "Anda harus login sebagai organizer untuk mengakses halaman ini."
        )
        return redirect("event_list")

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute(
            "SELECT organizer_id FROM ORGANIZER WHERE user_id = %s", [user_id]
        )
        organizer_row = cursor.fetchone()

    if not organizer_row:
        messages.error(request, "Data organizer tidak ditemukan.")
        return redirect("event_list")

    events = fetch_events(
        """
        SELECT e.event_id, e.event_datetime, e.event_title, e.venue_id, v.venue_name, e.organizer_id
        FROM EVENT e
        JOIN VENUE v ON v.venue_id = e.venue_id
        WHERE e.organizer_id = %s
        ORDER BY e.event_datetime
    """,
        [organizer_row[0]],
    )

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute(
            "SELECT venue_id, venue_name FROM VENUE ORDER BY city, venue_name"
        )
        venues = [
            {"venue_id": str(row[0]), "venue_name": row[1]} for row in cursor.fetchall()
        ]

        cursor.execute("SELECT artist_id, name FROM ARTIST ORDER BY name")
        artists = [
            {"artist_id": str(row[0]), "name": row[1]} for row in cursor.fetchall()
        ]

    return render(
        request,
        "event/my_event_list.html",
        {
            "role": "organizer",
            "events": events,
            "venues": venues,
            "artists": artists,
        },
    )


def save_event_artists(event, artist_ids):
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute("DELETE FROM EVENT_ARTIST WHERE event_id = %s", [event])
        for artist_id in artist_ids:
            if artist_id:
                cursor.execute(
                    "INSERT INTO EVENT_ARTIST (event_id, artist_id) VALUES (%s, %s)",
                    [event, artist_id],
                )


def save_event_categories(event, names, prices, quotas):
    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute("DELETE FROM TICKET_CATEGORY WHERE tevent_id = %s", [event])
        for name, price, quota in zip(names, prices, quotas):
            if name and price and quota:
                cursor.execute(
                    """
                    INSERT INTO TICKET_CATEGORY (category_id, category_name, price, quota, tevent_id)
                    VALUES (%s, %s, %s, %s, %s)
                """,
                    [uuid.uuid4(), name, price, quota, event],
                )


def create_event(request):
    role = get_current_role(request)
    if role not in ["admin", "organizer"]:
        messages.error(request, "Anda tidak memiliki akses untuk membuat event.")
        return redirect("event_list")

    if request.method == "POST":
        title = request.POST.get("event_title", "").strip()
        if not title:
            messages.error(request, "Judul event tidak boleh kosong.")
            return redirect("my_event_list" if role == "organizer" else "admin_event_list")
        date = request.POST.get("date")
        time = request.POST.get("time")
        venue_id = request.POST.get("venue_id")

        artist_ids = request.POST.getlist("artist_ids")
        category_names = request.POST.getlist("category_name")
        category_prices = request.POST.getlist("category_price")
        category_quotas = request.POST.getlist("category_quota")

        try:
            event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET search_path TO TikTakTuk, public")
                    if role == "organizer":
                        cursor.execute(
                            "SELECT organizer_id FROM ORGANIZER WHERE user_id = %s",
                            [request.session.get("user_id")],
                        )
                    else:
                        cursor.execute(
                            "SELECT organizer_id FROM ORGANIZER ORDER BY organizer_name LIMIT 1"
                        )
                    organizer_row = cursor.fetchone()

                    if not organizer_row:
                        messages.error(request, "Data organizer tidak ditemukan.")
                        return redirect(
                            "event_list" if role == "organizer" else "admin_event_list"
                        )

                    new_event_id = uuid.uuid4()

                    cursor.execute(
                        """
                        INSERT INTO EVENT (event_id, event_datetime, event_title, venue_id, organizer_id)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING event_id
                    """,
                        [
                            new_event_id,
                            event_datetime,
                            title,
                            venue_id,
                            organizer_row[0],
                        ],
                    )

                    created_event_id = cursor.fetchone()[0]

                save_event_artists(created_event_id, artist_ids)

                save_event_categories(
                    created_event_id,
                    category_names,
                    category_prices,
                    category_quotas,
                )

            messages.success(request, "Event berhasil dibuat.")

        except DatabaseError as e:
            messages.error(request, clean_db_error(e))
        except Exception as e:
            messages.error(request, f"Gagal membuat event: {e}")

    return redirect("my_event_list" if role == "organizer" else "admin_event_list")


def update_event(request, event_id):
    role = get_current_role(request)
    if role not in ["admin", "organizer"]:
        messages.error(request, "Anda tidak memiliki akses untuk mengubah event.")
        return redirect("event_list")

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        cursor.execute("SELECT organizer_id FROM EVENT WHERE event_id = %s", [event_id])
        event_row = cursor.fetchone()

    if not event_row:
        messages.error(request, "Event tidak ditemukan.")
        return redirect("event_list")

    if role == "organizer":
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")
            cursor.execute(
                "SELECT organizer_id FROM ORGANIZER WHERE user_id = %s",
                [request.session.get("user_id")],
            )
            organizer_row = cursor.fetchone()

        if not organizer_row or event_row[0] != organizer_row[0]:
            messages.error(
                request, "Organizer hanya dapat mengubah event miliknya sendiri."
            )
            return redirect("my_event_list")

    if request.method == "POST":
        title = request.POST.get("event_title", "").strip()
        if not title:
            messages.error(request, "Judul event tidak boleh kosong.")
            return redirect("my_event_list" if role == "organizer" else "admin_event_list")
        date = request.POST.get("date")
        time = request.POST.get("time")
        venue_id = request.POST.get("venue_id")
        event_datetime = datetime.strptime(
            f"{date} {time}",
            "%Y-%m-%d %H:%M"
        )
        artist_ids = request.POST.getlist("artist_ids")
        category_names = request.POST.getlist("category_name")
        category_prices = request.POST.getlist("category_price")
        category_quotas = request.POST.getlist("category_quota")

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET search_path TO TikTakTuk, public")
                    cursor.execute(
                        """
                        UPDATE EVENT
                        SET event_title = %s, event_datetime = %s, venue_id = %s
                        WHERE event_id = %s
                    """,
                        [
                            title,
                            event_datetime,
                            venue_id,
                            event_id,
                        ],
                    )

                save_event_artists(event_id, artist_ids)
                save_event_categories(
                    event_id, category_names, category_prices, category_quotas
                )

            messages.success(request, "Event berhasil diperbarui.")

        except DatabaseError as e:
            messages.error(request, clean_db_error(e))
        except Exception as e:
            messages.error(request, f"Gagal memperbarui event: {e}")

    return redirect("my_event_list" if role == "organizer" else "admin_event_list")


def checkout_view(request):
    event_id = request.GET.get("event")

    with connection.cursor() as cursor:
        cursor.execute("SET search_path TO TikTakTuk, public")
        if event_id:
            cursor.execute(
                """
                SELECT e.event_id, e.event_title, e.event_datetime, v.venue_name, v.jenis_seating, v.venue_id
                FROM EVENT e
                JOIN VENUE v ON v.venue_id = e.venue_id
                WHERE e.event_id = %s
                LIMIT 1
            """,
                [event_id],
            )
        else:
            cursor.execute("""
                SELECT e.event_id, e.event_title, e.event_datetime, v.venue_name, v.jenis_seating, v.venue_id
                FROM EVENT e
                JOIN VENUE v ON v.venue_id = e.venue_id
                WHERE e.event_datetime >= NOW()
                ORDER BY e.event_datetime ASC
                LIMIT 1
            """)
        event_row = cursor.fetchone()

    current_event = None
    categories = []
    seats = []
    promotions = []

    if event_row:
        current_event = {
            "event_id": str(event_row[0]),
            "event_title": event_row[1],
            "event_datetime": event_row[2],
            "venue_name": event_row[3],
            "jenis_seating": event_row[4],
            "venue_id": str(event_row[5]),
        }

        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")
            cursor.execute(
                """
                SELECT category_name, quota, price
                FROM TICKET_CATEGORY
                WHERE tevent_id = %s
                ORDER BY price DESC, category_name
            """,
                [current_event["event_id"]],
            )
            categories = [
                {"name": row[0], "quota": row[1], "price": row[2]}
                for row in cursor.fetchall()
            ]

            if current_event["jenis_seating"] == "Reserved Seating":
                cursor.execute(
                    """
                    SELECT s.seat_id, s.section, s.row_number, s.seat_number
                    FROM SEAT s
                    LEFT JOIN HAS_RELATIONSHIP hr ON hr.seat_id = s.seat_id
                    WHERE s.venue_id = %s AND hr.seat_id IS NULL
                    ORDER BY s.section, s.row_number, s.seat_number
                    LIMIT 24
                """,
                    [current_event["venue_id"]],
                )
                seats = [
                    {
                        "id": str(row[0]),
                        "label": f"{row[1]} - Baris {row[2]}, No. {row[3]}",
                    }
                    for row in cursor.fetchall()
                ]
            else:
                seats = [{"id": "tanpa_kursi", "label": "Tanpa Kursi"}]

            cursor.execute("""
                SELECT promo_code, discount_type, discount_value
                FROM PROMOTION
                WHERE start_date <= CURRENT_DATE AND end_date >= CURRENT_DATE
                ORDER BY start_date DESC
            """)
            promotions = [
                {
                    "promo_code": row[0],
                    "discount_type": row[1],
                    "discount_value": row[2],
                }
                for row in cursor.fetchall()
            ]

    if request.method == "POST":
        category = request.POST.get("ticket_category")
        quantity = int(request.POST.get("quantity", 0))
        seat = request.POST.get("seat", "")
        promo = request.POST.get("promo_code", "")

        category_lookup = {item["name"]: item for item in categories}

        if category not in category_lookup:
            messages.error(request, "Pilih kategori tiket yang valid.")
            return redirect(request.get_full_path())

        if quantity <= 0 or quantity > 10:
            messages.error(request, "Jumlah tiket harus antara 1 - 10 per transaksi.")
            return redirect(request.get_full_path())

        base_price = float(category_lookup[category]["price"])
        total_price = base_price * quantity

        if promo:
            promo_match = next(
                (item for item in promotions if item["promo_code"] == promo), None
            )
            if promo_match:
                if promo_match["discount_type"] == "PERCENTAGE":
                    total_price = total_price * (
                        1 - float(promo_match["discount_value"]) / 100
                    )
                else:
                    total_price = max(
                        0, total_price - float(promo_match["discount_value"])
                    )
            else:
                messages.error(request, "Kode promo tidak valid.")
                return redirect(request.get_full_path())

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    "SELECT customer_id FROM CUSTOMER ORDER BY full_name LIMIT 1"
                )
                cust_row = cursor.fetchone()
                if cust_row:
                    cursor.execute(
                        """
                        INSERT INTO "ORDER" (order_date, payment_status, total_amount, customer_id)
                        VALUES (NOW(), 'PENDING', %s, %s)
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

    return render(
        request,
        "order/checkout.html",
        {
            "event": current_event,
            "categories": categories,
            "seats": seats,
            "promotions": promotions,
        },
    )


def daftar_order_view(request):
    role = get_current_role(request)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")

            cursor.execute("""
                SELECT o.order_id, o.order_date, o.payment_status, o.total_amount, c.full_name, ua.username
                FROM "ORDER" o
                JOIN CUSTOMER c ON c.customer_id = o.customer_id
                JOIN USER_ACCOUNT ua ON ua.user_id = c.user_id
                ORDER BY o.order_date DESC
            """)
            orders = [
                {
                    "order_id": row[0],
                    "order_date": row[1],
                    "payment_status": row[2],
                    "total_amount": row[3],
                    "customer_name": row[4],
                    "customer_username": row[5],
                }
                for row in cursor.fetchall()
            ]

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
            if role in ["admin", "organizer"]:
                cursor.execute(
                    "SELECT COALESCE(SUM(total_amount), 0) FROM \"ORDER\" WHERE payment_status = 'LUNAS'"
                )
                revenue_res = cursor.fetchone()[0]
                total_revenue = revenue_res if revenue_res else 0

    except Exception as e:
        orders = []
        total_order = lunas_count = pending_count = total_revenue = 0

    context = {
        "orders": orders,
        "total_order": total_order,
        "lunas_count": lunas_count,
        "pending_count": pending_count,
        "total_revenue": total_revenue,
        "role": role,
    }
    return render(request, "order/order_list.html", context)


def update_order_status(request, order_id):
    if get_current_role(request) != "admin":
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
    if get_current_role(request) != "admin":
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
            SELECT p.promotion_id, p.promo_code, p.discount_type, p.discount_value, p.start_date, p.end_date, p.usage_limit,
                   COALESCE(COUNT(op.order_promotion_id), 0) AS current_usage
            FROM PROMOTION p
            LEFT JOIN ORDER_PROMOTION op ON op.promotion_id = p.promotion_id
            GROUP BY p.promotion_id, p.promo_code, p.discount_type, p.discount_value, p.start_date, p.end_date, p.usage_limit
            ORDER BY p.start_date DESC
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
                "current_usage": row[7],
            }
            for row in cursor.fetchall()
        ]

    total_promo = len(promotions)
    total_usage = sum(item["current_usage"] for item in promotions)
    total_percentage = sum(
        1 for item in promotions if item["discount_type"] == "PERCENTAGE"
    )

    context = {
        "promotions": promotions,
        "user_role": get_current_role(request),
        "total_promo": total_promo,
        "total_usage": total_usage,
        "total_percentage": total_percentage,
    }
    return render(request, "promotion/promotion_list.html", context)


def create_promotion(request):
    if get_current_role(request) != "admin":
        messages.error(request, "Akses ditolak!")
        return redirect("promotion_list")

    if request.method == "POST":
        try:
            discount_type = request.POST.get("discount_type")
            if discount_type == "Persentase":
                discount_type = "PERCENTAGE"
            elif discount_type == "Nominal":
                discount_type = "NOMINAL"

            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")
                cursor.execute(
                    """
                    INSERT INTO PROMOTION (promo_code, discount_type, discount_value, start_date, end_date, usage_limit)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    [
                        request.POST.get("promo_code").upper(),
                        discount_type,
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
    if get_current_role(request) != "admin":
        messages.error(request, "Akses ditolak!")
        return redirect("promotion_list")

    if request.method == "POST":
        try:
            discount_type = request.POST.get("discount_type")
            if discount_type == "Persentase":
                discount_type = "PERCENTAGE"
            elif discount_type == "Nominal":
                discount_type = "NOMINAL"

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
                        discount_type,
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
    if get_current_role(request) != "admin":
        messages.error(request, "Akses ditolak!")
        return redirect("promotion_list")

    if request.method == "POST":
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")
            cursor.execute("DELETE FROM PROMOTION WHERE promotion_id = %s", [promo_id])
        messages.success(request, "Data promo berhasil dihapus!")

    return redirect("promotion_list")