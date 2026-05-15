CREATE OR REPLACE FUNCTION TikTakTuk.check_event_artist_func() 
RETURNS TRIGGER AS $$
DECLARE
    v_artist_name VARCHAR;
    v_event_title VARCHAR;
BEGIN
    -- Memastikan Artist terdaftar di sistem
    IF NOT EXISTS (SELECT 1 FROM TikTakTuk.ARTIST WHERE artist_id = NEW.artist_id) THEN
        RAISE EXCEPTION 'Artist dengan ID % tidak ditemukan.', NEW.artist_id;
    END IF;

    -- Memastikan Event terdaftar di sistem
    IF NOT EXISTS (SELECT 1 FROM TikTakTuk.EVENT WHERE event_id = NEW.event_id) THEN
        RAISE EXCEPTION 'Event dengan ID % tidak ditemukan.', NEW.event_id;
    END IF;

    -- Mengambil nama artist dan judul event setelah dipastikan ada
    SELECT name INTO v_artist_name FROM TikTakTuk.ARTIST WHERE artist_id = NEW.artist_id;
    SELECT event_title INTO v_event_title FROM TikTakTuk.EVENT WHERE event_id = NEW.event_id;

    -- Memastikan tidak ada duplikasi Artist pada Event yang sama
    IF EXISTS (
        SELECT 1 FROM TikTakTuk.EVENT_ARTIST 
        WHERE artist_id = NEW.artist_id AND event_id = NEW.event_id
    ) THEN
        RAISE EXCEPTION 'Artist "%" sudah terdaftar pada event "%".', v_artist_name, v_event_title;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_event_artist ON TikTakTuk.EVENT_ARTIST;
CREATE TRIGGER trg_check_event_artist
BEFORE INSERT ON TikTakTuk.EVENT_ARTIST
FOR EACH ROW EXECUTE FUNCTION TikTakTuk.check_event_artist_func();

CREATE OR REPLACE FUNCTION TikTakTuk.get_sisa_kuota(p_event_id UUID)
RETURNS TABLE (category_name VARCHAR, sisa_kuota INTEGER) AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM TikTakTuk.EVENT WHERE event_id = p_event_id) THEN
        RAISE EXCEPTION 'Event dengan ID % tidak ditemukan.', p_event_id;
    END IF;

    RETURN QUERY
    SELECT tc.category_name,
           (tc.quota - CAST(COUNT(t.ticket_id) AS INTEGER))::INTEGER
    FROM TikTakTuk.TICKET_CATEGORY tc
    LEFT JOIN TikTakTuk.TICKET t ON t.tcategory_id = tc.category_id
    WHERE tc.tevent_id = p_event_id
    GROUP BY tc.category_id, tc.category_name, tc.quota;
END;
$$ LANGUAGE plpgsql;