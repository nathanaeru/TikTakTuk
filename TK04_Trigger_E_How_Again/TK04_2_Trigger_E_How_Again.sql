CREATE OR REPLACE FUNCTION check_venue_func() 
RETURNS TRIGGER AS $$
DECLARE
    existing_id UUID;
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        -- Mencegah duplikasi nama Venue di kota yang sama 
        SELECT venue_id INTO existing_id FROM TikTakTuk.VENUE
        WHERE LOWER(venue_name) = LOWER(NEW.venue_name) 
        AND LOWER(city) = LOWER(NEW.city) 
        AND venue_id != COALESCE(NEW.venue_id, '00000000-0000-0000-0000-000000000000');

        IF existing_id IS NOT NULL THEN
            RAISE EXCEPTION 'Venue "%" di kota "%" sudah terdaftar dengan ID %.', NEW.venue_name, NEW.city, existing_id;
        END IF;
        RETURN NEW;
        
    ELSIF TG_OP = 'DELETE' THEN
        -- Mencegah penghapusan Venue jika memiliki Event aktif 
        IF EXISTS (SELECT 1 FROM TikTakTuk.EVENT WHERE venue_id = OLD.venue_id) THEN
            RAISE EXCEPTION 'Venue "%" masih memiliki event aktif sehingga tidak dapat dihapus.', OLD.venue_name;
        END IF;
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_venue
BEFORE INSERT OR UPDATE OR DELETE ON TikTakTuk.VENUE
FOR EACH ROW EXECUTE FUNCTION check_venue_func();