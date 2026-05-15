from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.db import connection


def clean_db_error(e):
    """Ambil hanya baris pesan utama dari exception psycopg2 / trigger DB."""
    return str(e).split("CONTEXT:")[0].strip()


def choose_role_view(request):
    if "user_id" in request.session:
        return redirect("dashboard")
    return render(request, "auth/choose_role.html")


def register_customer_view(request):
    if "user_id" in request.session:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        full_name = request.POST.get("full_name")
        phone = request.POST.get("phone")

        if password != confirm_password:
            messages.error(request, "Password dan Konfirmasi Password tidak cocok!")
            return redirect("auth:register_customer")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")

                # 1. Insert Akun Utama (Trigger akan menangkap jika ada duplikasi)
                hashed_pw = make_password(password)
                cursor.execute(
                    "INSERT INTO USER_ACCOUNT (username, password) VALUES (%s, %s) RETURNING user_id",
                    [username, hashed_pw],
                )
                user_id = cursor.fetchone()[0]

                # 2. Petakan Role
                cursor.execute("SELECT role_id FROM ROLE WHERE role_name = 'customer'")
                role_id = cursor.fetchone()[0]
                cursor.execute(
                    "INSERT INTO ACCOUNT_ROLE (role_id, user_id) VALUES (%s, %s)",
                    [role_id, user_id],
                )

                # 3. Simpan Profil Customer
                cursor.execute(
                    "INSERT INTO CUSTOMER (full_name, phone_number, user_id) VALUES (%s, %s, %s)",
                    [full_name, phone, user_id],
                )

            messages.success(request, "Akun pelanggan berhasil dibuat! Silakan login.")
            return redirect("auth:login")

        except Exception as e:
            # Error message akan mengambil pesan RAISE EXCEPTION dari Trigger di database
            messages.error(request, f"Gagal mendaftar: {str(e)}")
            return redirect("auth:register_customer")

    return render(request, "auth/register_customer.html")


def register_organizer_view(request):
    if "user_id" in request.session:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        organizer_name = request.POST.get("organizer_name")
        email = request.POST.get("email")

        if password != confirm_password:
            messages.error(request, "Password dan Konfirmasi Password tidak cocok!")
            return redirect("auth:register_organizer")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")

                hashed_pw = make_password(password)
                cursor.execute(
                    "INSERT INTO USER_ACCOUNT (username, password) VALUES (%s, %s) RETURNING user_id",
                    [username, hashed_pw],
                )
                user_id = cursor.fetchone()[0]

                cursor.execute("SELECT role_id FROM ROLE WHERE role_name = 'organizer'")
                role_id = cursor.fetchone()[0]

                cursor.execute(
                    "INSERT INTO ACCOUNT_ROLE (role_id, user_id) VALUES (%s, %s)",
                    [role_id, user_id],
                )

                cursor.execute(
                    "INSERT INTO ORGANIZER (organizer_name, contact_email, user_id) VALUES (%s, %s, %s)",
                    [organizer_name, email, user_id],
                )

            messages.success(
                request, "Akun penyelenggara berhasil dibuat! Silakan login."
            )
            return redirect("auth:login")

        except Exception as e:
            messages.error(request, f"Gagal mendaftar: {str(e)}")
            return redirect("auth:register_organizer")

    return render(request, "auth/register_organizer.html")


def register_admin_view(request):
    if "user_id" in request.session:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Password dan Konfirmasi Password tidak cocok!")
            return redirect("auth:register_admin")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")

                hashed_pw = make_password(password)
                cursor.execute(
                    "INSERT INTO USER_ACCOUNT (username, password) VALUES (%s, %s) RETURNING user_id",
                    [username, hashed_pw],
                )
                user_id = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT role_id FROM ROLE WHERE role_name = 'administrator'"
                )
                role_id = cursor.fetchone()[0]

                cursor.execute(
                    "INSERT INTO ACCOUNT_ROLE (role_id, user_id) VALUES (%s, %s)",
                    [role_id, user_id],
                )

            messages.success(
                request, "Akun administrator berhasil dibuat! Silakan login."
            )
            return redirect("auth:login")

        except Exception as e:
            messages.error(request, f"Gagal mendaftar: {str(e)}")
            return redirect("auth:register_admin")

    return render(request, "auth/register_admin.html")


def login_view(request):
    if "user_id" in request.session:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")

                cursor.execute(
                    "SELECT user_id, username, password FROM USER_ACCOUNT WHERE username = %s",
                    [username],
                )
                user_row = cursor.fetchone()

                if user_row:
                    user_id, db_username, db_password = user_row

                    if check_password(password, db_password) or password == db_password:
                        cursor.execute(
                            """
                            SELECT r.role_name 
                            FROM ACCOUNT_ROLE ar
                            JOIN ROLE r ON ar.role_id = r.role_id
                            WHERE ar.user_id = %s
                        """,
                            [user_id],
                        )
                        role_row = cursor.fetchone()

                        if role_row:
                            request.session["user_id"] = str(user_id)
                            request.session["username"] = db_username
                            request.session["role"] = role_row[0].lower()
                            request.session.save()

                            messages.success(request, f"Selamat datang, {db_username}!")
                            return redirect("dashboard")
                        else:
                            messages.error(
                                request, "User tidak memiliki role yang valid."
                            )
                    else:
                        messages.error(request, "Username atau password salah!")
                else:
                    messages.error(request, "Username atau password salah!")

        except Exception as e:
            messages.error(request, f"Terjadi kesalahan: {e}")

    return render(request, "auth/login.html")


def logout_view(request):
    request.session.flush()
    messages.success(request, "Anda berhasil logout.")
    return redirect("auth:login")


def update_profile_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Silakan login terlebih dahulu.")
        return redirect("auth:login")

    if request.method != "POST":
        return redirect("dashboard_page", page="profile")

    role = request.session.get("role", "")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")

            if role == "customer":
                full_name = request.POST.get("full_name", "").strip()
                phone = request.POST.get("phone_number", "").strip()

                cursor.execute(
                    """
                    UPDATE CUSTOMER
                    SET full_name = %s, phone_number = %s
                    WHERE user_id = %s
                    """,
                    [full_name, phone, user_id],
                )

            elif role == "organizer":
                organizer_name = request.POST.get("organizer_name", "").strip()
                contact_email = request.POST.get("contact_email", "").strip()

                cursor.execute(
                    """
                    UPDATE ORGANIZER
                    SET organizer_name = %s, contact_email = %s
                    WHERE user_id = %s
                    """,
                    [organizer_name, contact_email, user_id],
                )

            else:
                # Admin tidak punya profil tambahan selain akun
                messages.info(request, "Tidak ada profil tambahan untuk role ini.")
                return redirect("dashboard_page", page="profile")

        messages.success(request, "Profil Anda berhasil diperbarui!")

    except Exception as e:
        messages.error(request, f"Gagal memperbarui profil: {clean_db_error(e)}")

    return redirect("dashboard_page", page="profile")


def update_password_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Silakan login terlebih dahulu.")
        return redirect("auth:login")

    if request.method != "POST":
        return redirect("dashboard_page", page="profile")

    old_password = request.POST.get("old_password", "")
    new_password = request.POST.get("new_password", "")
    confirm_password = request.POST.get("confirm_password", "")

    # ── Validasi
    if new_password != confirm_password:
        messages.error(request, "Password baru dan konfirmasi tidak cocok!")
        return redirect("dashboard_page", page="profile")

    if len(new_password) < 8:
        messages.error(request, "Error: Password minimal harus 8 karakter.")
        return redirect("dashboard_page", page="profile")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET search_path TO TikTakTuk, public")

            # Ambil password lama dari DB
            cursor.execute(
                "SELECT password FROM USER_ACCOUNT WHERE user_id = %s",
                [user_id],
            )
            row = cursor.fetchone()
            if not row:
                messages.error(request, "Akun tidak ditemukan.")
                return redirect("dashboard_page", page="profile")

            db_password = row[0]

            # Cek password lama (support hashed maupun plain untuk legacy data)
            if not (
                check_password(old_password, db_password) or old_password == db_password
            ):
                messages.error(request, "Password lama yang Anda masukkan salah.")
                return redirect("dashboard_page", page="profile")

            # Update password — trigger DB ikut memvalidasi panjang
            hashed_new = make_password(new_password)
            cursor.execute(
                "UPDATE USER_ACCOUNT SET password = %s WHERE user_id = %s",
                [hashed_new, user_id],
            )

        messages.success(request, "Password berhasil diperbarui!")

    except Exception as e:
        # Tangkap pesan dari trigger DB (misal panjang password)
        messages.error(request, clean_db_error(e))

    return redirect("dashboard_page", page="profile")


def change_password_view(request):
    # RBAC: Pastikan pengguna sudah login
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("auth:login")

    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Validasi dasar
        if new_password != confirm_password:
            messages.error(request, "Password baru dan konfirmasi tidak cocok.")
            return redirect("auth:profile")

        try:
            with connection.cursor() as cursor:
                cursor.execute("SET search_path TO TikTakTuk, public")

                # 1. Ambil password lama dari database untuk verifikasi
                cursor.execute(
                    "SELECT password FROM USER_ACCOUNT WHERE user_id = %s", [user_id]
                )
                row = cursor.fetchone()

                if row and check_password(old_password, row[0]):
                    # 2. Hash password baru dan update ke database
                    hashed_new_password = make_password(new_password)
                    cursor.execute(
                        "UPDATE USER_ACCOUNT SET password = %s WHERE user_id = %s",
                        [hashed_new_password, user_id],
                    )
                    messages.success(request, "Password berhasil diperbarui!")
                else:
                    messages.error(request, "Password lama yang Anda masukkan salah.")

        except Exception as e:
            messages.error(request, f"Terjadi kesalahan teknis: {str(e)}")

    return redirect("dashboard_page", page="profile")
