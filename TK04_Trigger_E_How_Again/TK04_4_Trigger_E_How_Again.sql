CREATE OR REPLACE FUNCTION TikTakTuk.check_order_promotion_func() 
RETURNS TRIGGER AS $$
DECLARE
    v_usage_limit INTEGER;
    v_current_usage INTEGER;
    v_start_date DATE;
    v_end_date DATE;
    v_event_date DATE;
BEGIN
    SELECT usage_limit, start_date, end_date INTO v_usage_limit, v_start_date, v_end_date
    FROM TikTakTuk.PROMOTION WHERE promotion_id = NEW.promotion_id;

    IF v_usage_limit IS NULL THEN
        RAISE EXCEPTION 'Promotion tidak ditemukan.';
    END IF;

    SELECT COUNT(*) INTO v_current_usage FROM TikTakTuk.ORDER_PROMOTION WHERE promotion_id = NEW.promotion_id;
    IF v_current_usage >= v_usage_limit THEN
        RAISE EXCEPTION 'Kuota promosi sudah habis.';
    END IF;

    -- Ambil tanggal event terkait order tersebut
    SELECT e.event_datetime::DATE INTO v_event_date
    FROM TikTakTuk."ORDER" o
    JOIN TikTakTuk.TICKET t ON t.torder_id = o.order_id
    JOIN TikTakTuk.TICKET_CATEGORY tc ON t.tcategory_id = tc.category_id
    JOIN TikTakTuk.EVENT e ON tc.tevent_id = e.event_id
    WHERE o.order_id = NEW.order_id LIMIT 1;

    IF v_event_date IS NOT NULL AND (v_event_date < v_start_date OR v_event_date > v_end_date) THEN
        RAISE EXCEPTION 'Tanggal event berada di luar periode promosi.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_order_promotion ON TikTakTuk.ORDER_PROMOTION;
CREATE TRIGGER trg_check_order_promotion
BEFORE INSERT ON TikTakTuk.ORDER_PROMOTION
FOR EACH ROW EXECUTE FUNCTION TikTakTuk.check_order_promotion_func();