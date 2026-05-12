# TikTakTuk

## Anggota Kelompok

- Alvino Revaldi - 2406438933
- Widya Mutia Ichsan - 2306165912
- Nathanael Leander Herdanatra - 2406421320
- Bryan Mitch - 2306165742

## Deployment Link

[https://web-production-cac588.up.railway.app/](https://web-production-cac588.up.railway.app/)

## Cara Setup Proyek

Requirement: Python versi 3.12+

1. Clone repositori ini.
2. Navigasi ke direktori proyek dan buat virtual environment:

    **Untuk Windows:**

    ```powershell
    python -m venv env
    ```

    **Untuk Unix/Linux atau MacOS:**

    ```bash
    python3 -m venv env
    ```

3. Aktifkan virtual environment:

    **Untuk Windows:**

    ```powershell
    env\Scripts\activate
    ```

    **Untuk Unix/Linux atau MacOS:**

    ```bash
    source env/bin/activate
    ```

4. Install dependencies yang diperlukan:

    ```bash
    pip install -r requirements.txt
    ```

5. Copy file `.env.example` menjadi `.env` dan isi dengan konfigurasi yang sesuai (seperti database credentials dan secret key). Untuk secret key merupakan string 50 karakter random, dapat di-generate dari [sini](https://djecrety.ir/).

6. Migrasi database:

    ```bash
    python manage.py migrate
    ```

7. Jalankan server development:

    ```bash
    python manage.py runserver
    ```

8. Buka URL localhost yang diberikan di terminal (biasanya `http://localhost:8000`) di browser Anda untuk melihat aplikasi berjalan.
