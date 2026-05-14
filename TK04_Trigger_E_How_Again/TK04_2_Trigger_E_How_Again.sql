CREATE OR REPLACE FUNCTION TikTakTuk.check_venue_func() 
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        IF EXISTS (
            SELECT 1 FROM TikTakTuk.VENUE
            WHERE LOWER(venue_name) = LOWER(NEW.venue_name) 
            AND LOWER(city) = LOWER(NEW.city) 
            AND venue_id IS DISTINCT FROM NEW.venue_id
        ) THEN
            RAISE EXCEPTION 'Venue "%" di kota "%" sudah ada.', NEW.venue_name, NEW.city;
        END IF;
        RETURN NEW;
        
    ELSIF TG_OP = 'DELETE' THEN
        IF EXISTS (SELECT 1 FROM TikTakTuk.EVENT WHERE venue_id = OLD.venue_id) THEN
            RAISE EXCEPTION 'Venue "%" tidak bisa dihapus karena masih ada event.', OLD.venue_name;
        END IF;
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_venue ON TikTakTuk.VENUE;
CREATE TRIGGER trg_check_venue
BEFORE INSERT OR UPDATE OR DELETE ON TikTakTuk.VENUE
FOR EACH ROW EXECUTE FUNCTION TikTakTuk.check_venue_func();