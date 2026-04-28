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
            return redirect("auth:register")  # Ditambahkan namespace 'auth:'

        if UserAccount.objects.filter(username=username).exists():
            messages.error(
                request, "Username sudah digunakan, silakan pilih yang lain."
            )
            return redirect("auth:register")

        try:
            with transaction.atomic():
                # 1. Buat Akun Utama dengan password yang di-hash
                new_user = UserAccount.objects.create(
                    username=username,
                    password=make_password(password),
                )

                # 2. Petakan Role secara aman
                # Menggunakan get_or_create mencegah error jika data 'role' belum di-seed di database
                role_obj, created = Role.objects.get_or_create(
                    role_name=role_type.lower()
                )
                AccountRole.objects.create(user=new_user, role=role_obj)

                # 3. Simpan ke profil spesifik (Customer / Organizer)
                if role_type == "customer":
                    Customer.objects.create(
                        full_name=full_name, phone_number=phone, user=new_user
                    )
                elif role_type == "organizer":
                    Organizer.objects.create(
                        organizer_name=full_name, contact_email=email, user=new_user
                    )

            messages.success(request, "Akun berhasil dibuat! Silakan login.")
            return redirect("auth:login")

        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat mendaftar: {str(e)}")
            return redirect("auth:register")

    return render(request, "auth/register.html")


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

                # Ambil role dengan aman (menggunakan filter & first untuk menghindari DoesNotExist error)
                account_role = (
                    AccountRole.objects.filter(user=user).select_related("role").first()
                )
                user_role = (
                    account_role.role.role_name.lower() if account_role else "guest"
                )

                # SET SESSION
                request.session["user_id"] = str(user.user_id)
                request.session["username"] = user.username
                request.session["role"] = user_role

                messages.success(request, f"Selamat datang, {user.username}!")

                # Arahkan ke dashboard di core/urls.py
                return redirect("dashboard")
            else:
                messages.error(request, "Password salah!")
        except UserAccount.DoesNotExist:
            messages.error(request, "Username tidak ditemukan!")

    return render(request, "auth/login.html")


def logout_view(request):
    # Hapus semua data session (logout)
    request.session.flush()
    messages.success(request, "Anda berhasil logout.")
    return redirect("auth:login")
