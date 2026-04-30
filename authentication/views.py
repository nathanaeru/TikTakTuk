from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from .models import UserAccount, Role, AccountRole, Customer, Organizer


def choose_role_view(request):
    """Halaman pilihan role sebelum registrasi"""
    if "user_id" in request.session:
        return redirect("dashboard")

    return render(request, "auth/choose_role.html")


def register_customer_view(request):
    """Registrasi untuk Pelanggan"""
    if "user_id" in request.session:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")

        # Validasi dasar
        if password != confirm_password:
            messages.error(request, "Password dan Konfirmasi Password tidak cocok!")
            return redirect("auth:register_customer")

        if UserAccount.objects.filter(username=username).exists():
            messages.error(
                request, "Username sudah digunakan, silakan pilih yang lain."
            )
            return redirect("auth:register_customer")

        try:
            with transaction.atomic():
                # 1. Buat Akun Utama dengan password yang di-hash
                new_user = UserAccount.objects.create(
                    username=username,
                    password=make_password(password),
                )

                # 2. Petakan Role
                role_obj, created = Role.objects.get_or_create(role_name="customer")
                AccountRole.objects.create(user=new_user, role=role_obj)

                # 3. Simpan ke profil Customer
                Customer.objects.create(
                    full_name=full_name, phone_number=phone, user=new_user
                )

            messages.success(request, "Akun pelanggan berhasil dibuat! Silakan login.")
            return redirect("auth:login")

        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat mendaftar: {str(e)}")
            return redirect("auth:register_customer")

    return render(request, "auth/register_customer.html")


def register_organizer_view(request):
    """Registrasi untuk Penyelenggara"""
    if "user_id" in request.session:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        organizer_name = request.POST.get("organizer_name")
        email = request.POST.get("email")

        # Validasi dasar
        if password != confirm_password:
            messages.error(request, "Password dan Konfirmasi Password tidak cocok!")
            return redirect("auth:register_organizer")

        if UserAccount.objects.filter(username=username).exists():
            messages.error(
                request, "Username sudah digunakan, silakan pilih yang lain."
            )
            return redirect("auth:register_organizer")

        try:
            with transaction.atomic():
                # 1. Buat Akun Utama dengan password yang di-hash
                new_user = UserAccount.objects.create(
                    username=username,
                    password=make_password(password),
                )

                # 2. Petakan Role
                role_obj, created = Role.objects.get_or_create(role_name="organizer")
                AccountRole.objects.create(user=new_user, role=role_obj)

                # 3. Simpan ke profil Organizer
                Organizer.objects.create(
                    organizer_name=organizer_name, contact_email=email, user=new_user
                )

            messages.success(
                request, "Akun penyelenggara berhasil dibuat! Silakan login."
            )
            return redirect("auth:login")

        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat mendaftar: {str(e)}")
            return redirect("auth:register_organizer")

    return render(request, "auth/register_organizer.html")


def register_admin_view(request):
    """Registrasi untuk Administrator"""
    if "user_id" in request.session:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        # Validasi dasar
        if password != confirm_password:
            messages.error(request, "Password dan Konfirmasi Password tidak cocok!")
            return redirect("auth:register_admin")

        if UserAccount.objects.filter(username=username).exists():
            messages.error(
                request, "Username sudah digunakan, silakan pilih yang lain."
            )
            return redirect("auth:register_admin")

        try:
            with transaction.atomic():
                # 1. Buat Akun Utama dengan password yang di-hash
                new_user = UserAccount.objects.create(
                    username=username,
                    password=make_password(password),
                )

                # 2. Petakan Role
                role_obj, created = Role.objects.get_or_create(
                    role_name="administrator"
                )
                AccountRole.objects.create(user=new_user, role=role_obj)

            messages.success(
                request, "Akun administrator berhasil dibuat! Silakan login."
            )
            return redirect("auth:login")

        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat mendaftar: {str(e)}")
            return redirect("auth:register_admin")

    return render(request, "auth/register_admin.html")


def login_view(request):
    # Jika user sudah memiliki session, arahkan langsung ke dashboard utama
    if "user_id" in request.session:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            # Cari user berdasarkan username
            user = UserAccount.objects.get(username=username)

            # Cocokkan password (hash dari register baru ATAU plaintext dari data dummy SQL)
            if check_password(password, user.password) or password == user.password:

                # Cek role user (harus tepat 1 role karena enforcment 1:n)
                user_role = (
                    AccountRole.objects.filter(user=user).select_related("role").first()
                )

                if user_role:
                    # Simpan user_id dan role ke session
                    request.session["user_id"] = str(user.user_id)
                    request.session["username"] = user.username
                    request.session["role"] = user_role.role.role_name.lower()
                    request.session.save()

                    messages.success(request, f"Selamat datang, {user.username}!")
                    return redirect("dashboard")
                else:
                    # User tidak memiliki role (seharusnya tidak terjadi)
                    messages.error(request, "User tidak memiliki role yang valid.")
            else:
                messages.error(request, "Username atau password salah!")
        except UserAccount.DoesNotExist:
            messages.error(request, "Username atau password salah!")

    return render(request, "auth/login.html")


def logout_view(request):
    # Hapus semua data session (logout)
    request.session.flush()
    messages.success(request, "Anda berhasil logout.")
    return redirect("auth:login")


# DEPRECATED: select_role_view no longer needed since each user has exactly 1 role (1:n relationship)
# def select_role_view(request):
#     """
#     Halaman pemilihan role (DEPRECATED)
#     Dengan enforcement 1:n, setiap user hanya bisa punya 1 role.
#     Jadi flow login langsung set role dari database.
#     """
#     pass
