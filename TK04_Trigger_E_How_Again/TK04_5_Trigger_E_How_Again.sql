CREATE OR REPLACE FUNCTION TikTakTuk.check_seat_delete_func() 
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM TikTakTuk.HAS_RELATIONSHIP WHERE seat_id = OLD.seat_id) THEN
        RAISE EXCEPTION 'Kursi % Baris % No. % tidak dapat dihapus karena sudah terisi.', OLD.section, OLD.row_number, OLD.seat_number;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_seat_delete ON TikTakTuk.SEAT;
CREATE TRIGGER trg_check_seat_delete
BEFORE DELETE ON TikTakTuk.SEAT
FOR EACH ROW EXECUTE FUNCTION TikTakTuk.check_seat_delete_func();

CREATE OR REPLACE FUNCTION TikTakTuk.check_ticket_quota_func() 
RETURNS TRIGGER AS $$
DECLARE
    v_quota INTEGER;
    v_sold INTEGER;
    v_category_name VARCHAR;
BEGIN
    SELECT quota, category_name INTO v_quota, v_category_name
    FROM TikTakTuk.TICKET_CATEGORY WHERE category_id = NEW.tcategory_id;

    SELECT COUNT(*) INTO v_sold FROM TikTakTuk.TICKET WHERE tcategory_id = NEW.tcategory_id;

    IF v_sold >= v_quota THEN
        RAISE EXCEPTION 'Kuota kategori tiket "%" sudah penuh.', v_category_name;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_ticket_quota ON TikTakTuk.TICKET;
CREATE TRIGGER trg_check_ticket_quota
BEFORE INSERT ON TikTakTuk.TICKET
FOR EACH ROW EXECUTE FUNCTION TikTakTuk.check_ticket_quota_func();