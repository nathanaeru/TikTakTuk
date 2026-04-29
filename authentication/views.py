from django.shortcuts import render, redirect, get_object_or_404
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

                # Cek jumlah role yang dimiliki user
                user_roles = AccountRole.objects.filter(user=user).select_related(
                    "role"
                )
                roles_count = user_roles.count()

                # Simpan user_id ke session sementara untuk proses selanjutnya
                request.session["user_id"] = str(user.user_id)
                request.session["username"] = user.username

                # Jika user memiliki lebih dari satu role, arahkan ke halaman pemilihan role
                if roles_count > 1:
                    request.session["pending_role_selection"] = True
                    messages.info(
                        request, "Silakan pilih role yang ingin Anda gunakan!"
                    )
                    return redirect("auth:select_role")
                elif roles_count == 1:
                    # Jika hanya satu role, langsung set session dan arahkan ke dashboard
                    user_role = user_roles.first().role.role_name.lower()
                    request.session["role"] = user_role
                    messages.success(request, f"Selamat datang, {user.username}!")
                    return redirect("dashboard")
                else:
                    # User tidak memiliki role, set sebagai guest
                    request.session["role"] = "guest"
                    messages.success(request, f"Selamat datang, {user.username}!")
                    return redirect("dashboard")
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


def select_role_view(request):
    # Pastikan user dalam proses login dan belum memilih role
    user_id = request.session.get("user_id")
    pending_role_selection = request.session.get("pending_role_selection", False)

    if not user_id or not pending_role_selection:
        return redirect("auth:login")

    user = get_object_or_404(UserAccount, user_id=user_id)
    user_roles = AccountRole.objects.filter(user=user).select_related("role")

    if request.method == "POST":
        selected_role_id = request.POST.get("role_id")

        try:
            selected_role = AccountRole.objects.select_related("role").get(
                user=user, role_id=selected_role_id
            )
            # Set role ke session dan hapus flag pending_role_selection
            request.session["role"] = selected_role.role.role_name.lower()
            del request.session["pending_role_selection"]
            request.session.save()

            messages.success(
                request,
                f"Anda login dengan role: {selected_role.role.role_name.upper()}",
            )
            return redirect("dashboard")
        except AccountRole.DoesNotExist:
            messages.error(request, "Role tidak ditemukan!")

    roles = [
        {
            "role_id": ar.role.role_id,
            "role_name": ar.role.role_name.upper(),
        }
        for ar in user_roles
    ]

    context = {
        "username": user.username,
        "roles": roles,
    }

    return render(request, "auth/select_role.html", context)
