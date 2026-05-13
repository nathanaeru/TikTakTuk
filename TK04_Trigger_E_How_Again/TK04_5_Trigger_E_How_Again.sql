-- Trigger 5.1: Memeriksa keterikatan kursi 
CREATE OR REPLACE FUNCTION check_seat_delete_func() 
RETURNS TRIGGER AS $$

BEGIN
    NEW
    IF EXISTS (SELECT 1 FROM TikTakTuk.HAS_RELATIONSHIP WHERE seat_id = OLD.seat_id) THEN
        RAISE EXCEPTION 'Kursi % Baris % No. % tidak dapat dihapus karena sudah terisi.', OLD.section, OLD.row_number, OLD.seat_number;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_seat_delete
BEFORE DELETE ON TikTakTuk.SEAT
FOR EACH ROW 
EXECUTE FUNCTION check_seat_delete_func();

-- Trigger 5.2: Memeriksa dan memastikan kuota kategori tiket [cite: 422]
CREATE OR REPLACE FUNCTION check_ticket_quota_func() 
RETURNS TRIGGER AS $$
DECLARE
    v_quota INTEGER;
    v_sold INTEGER;
    v_category_name VARCHAR;
BEGIN
    -- (asumsi) kalo misal ada update di tiket, perlu cek kuota karena bisa jadi pindah ke kategori yang berbeda yang mungkin udah penuh
    SELECT quota, category_name INTO v_quota, v_category_name
    FROM TikTakTuk.TICKET_CATEGORY 
    WHERE category_id = NEW.tcategory_id;

    -- hitung jumlah tiket yang sudah terjual untuk kategori tiket make aggregate 
    SELECT COUNT(*) INTO v_sold
    FROM TikTakTuk.TICKET 
    WHERE tcategory_id = NEW.tcategory_id;

    -- cek kuota kategori
    IF v_sold >= v_quota THEN
        RAISE EXCEPTION 'Kuota kategori tiket "%" sudah penuh. Tidak dapat membuat tiket baru.', v_category_name;
    END IF;

    -- (asumsi) cek kalo misal ada seat yang  dipilih ternyata udah diassign ke tiket lain
    IF NEW.seat_id IS NOT NULL THEN
    -- cek kalo kursi sudah diambil tiket lain
    IF EXISTS (
        SELECT 1 
        FROM TikTakTuk.TICKET 
        WHERE seat_id = NEW.seat_id AND ticket_id IS DISTINCT FROM NEW.ticket_id
    ) THEN
        RAISE EXCEPTION 'ERROR: Kursi dengan ID % sudah terisi oleh tiket lain. Silakan pilih kursi yang berbeda.', NEW.seat_id;
    END IF;
END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_ticket_quota
BEFORE INSERT ON TikTakTuk.TICKET
FOR EACH ROW EXECUTE FUNCTION check_ticket_quota_func();