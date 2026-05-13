CREATE OR REPLACE FUNCTION check_username_func() 
RETURNS TRIGGER AS $$
BEGIN

    -- (asumsi) Mencegah jika usernamene dimasukkan dengan tambahan spasi baik di awal maupun akhir
    NEW.username := TRIM(NEW.username); 

    -- Mencegah username dengan karakter spesial 
    IF NEW.username !~ '^[a-zA-Z0-9]+$' THEN
        RAISE EXCEPTION 'Username "%" hanya boleh mengandung huruf dan angka tanpa simbol atau spasi.', NEW.username;
    END IF;

    -- Pengecekan username unik (case-insensitive) 
    IF EXISTS (
        SELECT 1 FROM TikTakTuk.USER_ACCOUNT 
        WHERE LOWER(username) = LOWER(NEW.username) 
        AND user_id IS DISTINCT FROM NEW.user_id 
    ) THEN
        RAISE EXCEPTION 'Username "%" sudah terdaftar, gunakan username lain.', NEW.username;

    -- (asumsi) nambahin validasi biar password minimalnya 8 karakter dan ga mudah ditebak agar menjamin keamanan akun 
    IF LENGTH(NEW.password) < 8 THEN
    RAISE EXCEPTION 'Error: Password minimal harus 8 karakter.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_username
BEFORE INSERT OR UPDATE ON TikTakTuk.USER_ACCOUNT
FOR EACH ROW 
EXECUTE FUNCTION check_username_func();