from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.db import connection


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
