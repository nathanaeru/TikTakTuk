# Refactor Dokumentasi: Implementasi 1:N Role-User Relationship

## 📋 Ringkasan Perubahan

Telah berhasil merefactor aplikasi TikTakTuk dengan implementasi 1:N relationship antara User dan Role, di mana:

- **Setiap user hanya boleh memiliki TEPAT 1 role** (customer, organizer, atau administrator)
- **Halaman registrasi terpisah** untuk setiap role dengan form yang spesifik
- **Role selection flow** sebelum registrasi untuk memandu user
- **DML bersih** tanpa duplicate roles, dengan >= 15 rows data

---

## 🏗️ Perubahan Struktur

### 1. **Halaman Baru (Templates)**

#### `templates/auth/choose_role.html` ✨

- Halaman pemilihan role **PRE-REGISTRASI**
- Design responsif dengan 3 kartu untuk: Pelanggan, Penyelenggara, Administrator
- Link langsung ke halaman registrasi masing-masing role
- Link ke login untuk user yang sudah terdaftar

#### `templates/auth/register_customer.html` ✨

- Form khusus untuk registrasi **Pelanggan**
- Field: Nama Lengkap, Username, Email, Nomor Telepon, Password
- Simpan ke table `CUSTOMER`

#### `templates/auth/register_organizer.html` ✨

- Form khusus untuk registrasi **Penyelenggara**
- Field: Nama Organisasi, Username, Email Kontak, Password
- Simpan ke table `ORGANIZER`

#### `templates/auth/register_admin.html` ✨

- Form khusus untuk registrasi **Administrator** (terbatas)
- Memerlukan **kode akses admin** untuk verifikasi
- Field: Kode Akses, Nama Lengkap, Username, Email, Password
- Simpan langsung ke `USER_ACCOUNT` (tidak perlu profile terpisah)

---

### 2. **Views Refactor** (`authentication/views.py`)

#### `choose_role_view(request)` ✨

- Render halaman pilihan role (`choose_role.html`)
- Entry point baru untuk flow registrasi

#### `register_customer_view(request)` ✨

- Proses registrasi khusus **Pelanggan**
- Auto-assign role "customer" ke user
- Create customer profile dengan data yang diinput
- Validasi: username unique, password match

#### `register_organizer_view(request)` ✨

- Proses registrasi khusus **Penyelenggara**
- Auto-assign role "organizer" ke user
- Create organizer profile
- Validasi: username unique, password match

#### `register_admin_view(request)` ✨

- Proses registrasi khusus **Administrator**
- Verifikasi **admin access code** (`ADMIN2026SECRET`)
- Auto-assign role "administrator" ke user
- Validasi: admin code correct, username unique, password match

#### `login_view(request)` ✅ SIMPLIFIED

- **TIDAK lagi perlu role selection page** ❌
- Langsung ambil 1 role dari `AccountRole` table
- Set session: `user_id`, `username`, `role`
- Redirect ke dashboard

#### `select_role_view(request)` ❌ DEPRECATED

- Tidak lagi digunakan karena enforcement 1:n
- Silenced dalam view (commented out)
- Kept untuk backward compatibility

---

### 3. **URL Routes** (`authentication/urls.py`)

```python
urlpatterns = [
    path("choose-role/", views.choose_role_view, name="choose_role"),
    path("register/customer/", views.register_customer_view, name="register_customer"),
    path("register/organizer/", views.register_organizer_view, name="register_organizer"),
    path("register/admin/", views.register_admin_view, name="register_admin"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Legacy URLs (backward compatibility)
    path("register/", views.choose_role_view, name="register"),
]
```

---

### 4. **Model Constraint** (`authentication/models.py`)

#### `AccountRole` Model Update

```python
constraints = [
    models.UniqueConstraint(
        fields=["user_id"],
        name="one_role_per_user",
        violation_error_message="Setiap user hanya boleh memiliki 1 role"
    )
]
```

- **Enforced 1:N relationship** di level aplikasi
- Mencegah duplicate roles untuk user yang sama

---

### 5. **SQL DML Update** (`TK03_DUMP_SQL_E_How Again.sql`)

#### Data Bersih & Konsisten ✨

**USER_ACCOUNT (16 users):**

- 2 Administrators: `admin_naeru`, `admin_nabeel`
- 4 Organizers: `org_andiwijaya`, `org_javajazz`, `org_soundrenaline`, `org_wefest`
- 10 Customers: `cust_budi`, `cust_siti`, `cust_joko`, `cust_rini`, `cust_andi`, `cust_maya`, `cust_eka`, `cust_luna`, `cust_zara`, `cust_tomas`

**ACCOUNT_ROLE (16 rows - NO DUPLICATES):**

- 2 rows: Admin roles
- 4 rows: Organizer roles
- 10 rows: Customer roles
- **Total: 16 rows (>= 15 requirement ✓)**

**CUSTOMER (10 rows - Updated):**

- Added 4 new customers: Eka Putri, Luna Wijaya, Zara Malik, Tomas Hidayat

**Removed Duplicates:**

- ❌ Removed: admin_naeru dengan customer role
- ❌ Removed: admin_nabeel dengan customer role
- ❌ Removed: org_andiwijaya dengan customer role

---

## 🔄 Flow Perubahan

### **OLD Flow (Before):**

```
Login
  ↓
Select Role (if user has multiple roles)
  ↓
Dashboard
```

### **OLD Registration (Before):**

```
Single Register Page (with radio button)
  ↓
Create User + AccountRole (could have multiple)
  ↓
Create Customer/Organizer/Admin Profile
  ↓
Login
```

### **NEW Flow (After):**

```
Auth Home
  ↓
Choose Role
  ├→ Register Customer
  ├→ Register Organizer
  └→ Register Admin (with access code)
  ↓
Create User + AccountRole (exactly 1)
  ↓
Create Role-Specific Profile
  ↓
Login
  ↓
Dashboard (directly, no role selection needed)
```

---

## ✅ Verification Checklist

### Data Integrity:

- [x] Setiap user punya **tepat 1 role**
- [x] Tidak ada **duplicate roles** per user
- [x] Total **ACCOUNT_ROLE >= 15 rows** (16 rows ✓)
- [x] Semua users memiliki profile yang sesuai (Customer/Organizer)
- [x] Admins **tidak perlu profile terpisah**

### Code Integrity:

- [x] Views: Role selection pre-registration ✓
- [x] Views: 3 registration endpoints (customer/organizer/admin) ✓
- [x] Views: Simplified login (no role selection) ✓
- [x] URLs: All routes configured ✓
- [x] Models: 1:N constraint added ✓
- [x] Templates: 4 halaman baru ✓

### Backward Compatibility:

- [x] Old `/register/` URL masih berfungsi (redirect ke choose_role)
- [x] Existing select_role_view commented out (not removed)
- [x] Session variables tetap konsisten

---

## 🚀 Cara Test

### 1. **Reset Database**

```bash
psql -U postgres < TK03_DUMP_SQL_E_How Again.sql
```

### 2. **Test Registration Flow**

```
http://localhost:8000/auth/choose-role/
  ↓ (click "Daftar Sebagai Pelanggan")
http://localhost:8000/auth/register/customer/
  ↓ (fill form & submit)
Redirect ke login
```

### 3. **Test Login**

```
Username: cust_budi
Password: hashpass123
Expected: Direct to dashboard (no role selection)
```

### 4. **Test Admin Registration** (optional)

```
http://localhost:8000/auth/register/admin/
Admin Code: ADMIN2026SECRET
Submit → Should work
```

---

## 📝 Environment Variable

Update `.env` atau `settings.py` jika ingin customize admin access code:

```python
# settings.py / views.py
ADMIN_ACCESS_CODE = os.getenv("ADMIN_ACCESS_CODE", "ADMIN2026SECRET")
```

---

## ⚠️ Important Notes

1. **Admin Access Code** (`ADMIN2026SECRET`) - Ganti di production!
2. **Password Hashing** - Semua password baru sudah di-hash dengan `make_password()`
3. **Backward Compatibility** - Old `/register/` URL tetap jalan
4. **Database Migration** - Jika sudah ada data lama, perlu cleanup duplicate roles terlebih dahulu
5. **Select Role Deprecated** - `select_role_view` tidak lagi dipanggil dari login

---

## 📊 Data Comparison

### BEFORE (16 rows dengan duplicates):

```
admin_naeru      → ADMIN, CUSTOMER ❌
admin_nabeel     → ADMIN, CUSTOMER ❌
org_andiwijaya   → ORGANIZER, CUSTOMER ❌
org_javajazz     → ORGANIZER
org_soundrenaline→ ORGANIZER
org_wefest       → ORGANIZER
cust_budi        → CUSTOMER
... (6 customers)
```

### AFTER (16 rows, clean):

```
admin_naeru      → ADMINISTRATOR ✓
admin_nabeel     → ADMINISTRATOR ✓
org_andiwijaya   → ORGANIZER ✓
org_javajazz     → ORGANIZER ✓
org_soundrenaline→ ORGANIZER ✓
org_wefest       → ORGANIZER ✓
cust_budi...     → CUSTOMER ✓
cust_eka         → CUSTOMER ✓
cust_luna        → CUSTOMER ✓
cust_zara        → CUSTOMER ✓
cust_tomas       → CUSTOMER ✓
```

---

## 🎉 Hasil Akhir

✅ **1:N Relationship** - Setiap user tepat 1 role  
✅ **Separate Registration** - 3 halaman registrasi role-specific  
✅ **Role Selection** - Pre-registration flow yang clear  
✅ **Clean DML** - Tanpa duplicate, >= 15 rows  
✅ **Backward Compatible** - Old URLs tetap jalan  
✅ **Simplified Login** - Tidak perlu role selection lagi

Refactor selesai! 🚀
