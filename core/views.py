from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages

def home_view(request):
    """Halaman utama TikTakTuk"""
    return render(request, 'home.html')

def dashboard_pengguna(request, user_id=None, page='main'):
    """
    Fungsi tunggal untuk mengelola Dashboard (Admin, Organizer, Customer) 
    dan Profil Pengguna secara dinamis.
    """
    # USER GUEST
    if user_id is None:
        with connection.cursor() as cursor:
            cursor.execute('SET search_path TO tiktaktuk, public')
            cursor.execute('''
                SELECT e.event_title, e.event_datetime, v.venue_name 
                FROM EVENT e 
                JOIN VENUE v ON e.venue_id = v.venue_id 
                LIMIT 3
            ''')
            trending_events = cursor.fetchall()

        context = {
            'username': 'Guest', 
            'nama': 'Pengunjung Baru',
            'is_guest': True,
            'page': page,
            'trending_events': trending_events
        }
        
        if page == 'profile':
            context.update({'nama_lengkap': 'Pengunjung Baru', 'nomor_telepon': '-', 'role_display': 'Guest'})
            return render(request, 'dashboard/profile.html', context)
            
        return render(request, 'dashboard/customer.html', context)

    # USER LOGIN 
    with connection.cursor() as cursor:
        cursor.execute('SET search_path TO tiktaktuk, public')
        
        # UPDATE PROFIL (POST)
        if request.method == 'POST' and page == 'profile':
            nama_baru = request.POST.get('nama_lengkap')
            telp_baru = request.POST.get('nomor_telepon')
            
            # Cek role usernya
            cursor.execute('SELECT role_id FROM account_role WHERE user_id = %s', [user_id])
            # update logic
            
            cursor.execute('''
                UPDATE customer SET full_name = %s, phone_number = %s WHERE user_id = %s
            ''', [nama_baru, telp_baru, user_id])
            
            messages.success(request, "Profil Anda berhasil diperbarui!")
            return redirect('dashboard_page', user_id=user_id, page='profile')

        cursor.execute('''
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
        ''', [user_id])
        
        user_data = cursor.fetchone()
        if not user_data:
            return render(request, 'error.html', {'message': 'User tidak ditemukan'})
        
        username, full_name, phone_number, organizer_name, cust_id, uid = user_data
        
        # CEK ROLE
        cursor.execute('''
            SELECT r.role_name FROM account_role ar
            JOIN role r ON ar.role_id = r.role_id
            WHERE ar.user_id = %s
        ''', [user_id])
        
        role_fetch = cursor.fetchone()
        raw_role_name = role_fetch[0].lower() if role_fetch else "customer"
        
        # Mapping Role Display
        if raw_role_name == 'administrator':
            role_display = "admin"
        elif raw_role_name == 'organizer':
            role_display = "organizer"
        else:
            role_display = "customer"

        context = {
            'username': username, 
            'user_id': user_id, 
            'is_guest': False, 
            'page': page,
            'role': role_display
        }

        # ======================== VIEW: PROFIL ========================
        if page == 'profile':
            display_name = organizer_name if role_display == 'organizer' else (full_name or username)
            context.update({
                'nama_lengkap': display_name,
                'nomor_telepon': phone_number or '-',
                'role_display': raw_role_name.capitalize()
            })
            return render(request, 'dashboard/profile.html', context)

        # ======================== VIEW: DASHBOARD ========================
        if role_display == 'customer':
            # Statistik Dashboard Customer
            cursor.execute('''
                SELECT COUNT(t.ticket_id) FROM TICKET t
                JOIN "ORDER" o ON t.torder_id = o.order_id
                JOIN TICKET_CATEGORY tc ON t.tcategory_id = tc.category_id
                JOIN EVENT e ON tc.tevent_id = e.event_id
                WHERE o.customer_id = %s AND e.event_datetime >= CURRENT_TIMESTAMP
            ''', [cust_id])
            tiket_aktif = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(DISTINCT order_id) FROM "ORDER" WHERE customer_id = %s', [cust_id])
            total_acara = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM PROMOTION WHERE end_date >= CURRENT_DATE')
            kode_promo = cursor.fetchone()[0]

            cursor.execute('SELECT COALESCE(SUM(total_amount), 0) FROM "ORDER" WHERE customer_id = %s', [cust_id])
            belanja = float(cursor.fetchone()[0])
            belanja_display = f"Rp {belanja / 1000000:.1f}M" if belanja >= 1000000 else f"Rp {int(belanja/1000)}K"

            # List Tiket
            cursor.execute('''
                SELECT e.event_title, e.event_datetime, v.venue_name, tc.category_name
                FROM TICKET t
                JOIN "ORDER" o ON t.torder_id = o.order_id
                JOIN TICKET_CATEGORY tc ON t.tcategory_id = tc.category_id
                JOIN EVENT e ON tc.tevent_id = e.event_id
                JOIN VENUE v ON e.venue_id = v.venue_id
                WHERE o.customer_id = %s AND e.event_datetime >= CURRENT_TIMESTAMP
                ORDER BY e.event_datetime ASC LIMIT 2
            ''', [cust_id])
            tiket_list = cursor.fetchall()

            context.update({
                'nama': full_name or username,
                'tiket_aktif': tiket_aktif,
                'total_acara': total_acara,
                'kode_promo': kode_promo,
                'total_belanja': belanja_display,
                'tiket_list': tiket_list
            })
        
        elif role_display == 'admin':
            context.update({'nama': 'System Console'})
            
        else: # ROLE ORGANIZER
            cursor.execute('SELECT COUNT(*) FROM EVENT WHERE organizer_id = (SELECT organizer_id FROM organizer WHERE user_id = %s)', [user_id])
            count_event = cursor.fetchone()[0]
            
            context.update({
                'nama': organizer_name or username,
                'count_event': count_event
            })

    return render(request, f'dashboard/{role_display}.html', context)