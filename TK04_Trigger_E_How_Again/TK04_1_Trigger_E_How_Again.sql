CREATE OR REPLACE FUNCTION TikTakTuk.check_username_func() 
RETURNS TRIGGER AS $$
BEGIN
    NEW.username := TRIM(NEW.username); 

    IF NEW.username !~ '^[a-zA-Z0-9]+$' THEN
        RAISE EXCEPTION 'Username "%" hanya boleh mengandung huruf dan angka.', NEW.username;
    END IF;

    IF EXISTS (
        SELECT 1 FROM TikTakTuk.USER_ACCOUNT 
        WHERE LOWER(username) = LOWER(NEW.username) 
        AND user_id IS DISTINCT FROM NEW.user_id 
    ) THEN
        RAISE EXCEPTION 'Username "%" sudah terdaftar, gunakan username lain.', NEW.username;
    END IF;

    IF LENGTH(NEW.password) < 8 THEN
        RAISE EXCEPTION 'Password minimal harus 8 karakter.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_username ON TikTakTuk.USER_ACCOUNT;
CREATE TRIGGER trg_check_username
BEFORE INSERT OR UPDATE ON TikTakTuk.USER_ACCOUNT
FOR EACH ROW EXECUTE FUNCTION TikTakTuk.check_username_func();