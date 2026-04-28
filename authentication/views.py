from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from .models import UserAccount, Role, AccountRole, Customer, Organizer


def register_view(request):
    if request.method == "POST":
        role_type = request.POST.get("role")
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")

        # Validasi dasar
        if password != confirm_password:
            messages.error(request, "Password dan Konfirmasi Password tidak cocok!")
            return redirect("register")

        if UserAccount.objects.filter(username=username).exists():
            messages.error(
                request, "Username sudah digunakan, silakan pilih yang lain."
            )
            return redirect("register")

        try:
            with transaction.atomic():
                # 1. Buat Akun Utama
                new_user = UserAccount.objects.create(
                    username=username,
                    password=make_password(password),  # Enkripsi password
                )

                # 2. Petakan Role
                role_obj = Role.objects.get(role_name=role_type)
                AccountRole.objects.create(user=new_user, role=role_obj)

                # 3. Simpan ke tabel spesifik
                if role_type == "customer":
                    Customer.objects.create(
                        full_name=full_name, phone_number=phone, user=new_user
                    )
                elif role_type == "organizer":
                    Organizer.objects.create(
                        organizer_name=full_name, contact_email=email, user=new_user
                    )

            messages.success(request, "Akun berhasil dibuat! Silakan login.")
            return redirect("login")

        except Exception as e:
            messages.error(request, f"Terjadi kesalahan: {str(e)}")
            return redirect("register")

    return render(request, "auth/register.html")


def login_view(request):
    # Jika user sudah login, langsung arahkan ke dashboard
    if "user_id" in request.session:
        return redirect("dashboard")  # Ganti 'dashboard' dengan nama URL dashboard Anda

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            # Cari user berdasarkan username
            user = UserAccount.objects.get(username=username)

            # Cocokkan password
            if check_password(password, user.password) or password == user.password:
                # (Catatan: 'password == user.password' ditambahkan untuk mentoleransi
                # data dummy SQL awal yang mungkin belum di-hash)

                # Ambil role dari tabel AccountRole
                user_role = AccountRole.objects.get(user=user).role.role_name

                # SET SESSION
                request.session["user_id"] = str(user.user_id)
                request.session["username"] = user.username
                request.session["role"] = user_role

                messages.success(request, f"Selamat datang, {user.username}!")

                # Arahkan berdasarkan role
                return redirect("dashboard")
            else:
                messages.error(request, "Password salah!")
        except UserAccount.DoesNotExist:
            messages.error(request, "Username tidak ditemukan!")

    return render(request, "auth/login.html")


def logout_view(request):
    # Hapus semua data session
    request.session.flush()
    messages.success(request, "Anda berhasil logout.")
    return redirect("login")
