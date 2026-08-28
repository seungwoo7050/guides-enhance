-- [Implementation 2] 조건부 UPDATE로 재고를 예약합니다.
-- 수량 확인과 차감을 한 문장에 넣어 같은 재고 행을 갱신하는 요청끼리 순서대로 처리되게 합니다.
CREATE OR REPLACE FUNCTION reserve_inventory(p_sku text, p_quantity integer)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE changed integer;
BEGIN
    IF p_quantity <= 0 THEN
        RAISE EXCEPTION 'quantity must be positive';
    END IF;

    UPDATE inventory
    SET available = available - p_quantity
    WHERE sku = p_sku
      AND available >= p_quantity;
    GET DIAGNOSTICS changed = ROW_COUNT;
    RETURN changed = 1;
END $$;

-- [Implementation 3] 여러 의사 행에 걸친 당직 조건을 공용 guard로 보호합니다.
-- 당직자를 줄일 수 있는 모든 함수가 먼저 shift_guard의 같은 행을 잠근 뒤 인원 수를 확인합니다.
CREATE OR REPLACE FUNCTION take_off_call(p_doctor_id integer)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE active_count integer;
DECLARE changed integer;
BEGIN
    PERFORM id FROM shift_guard WHERE id = 1 FOR UPDATE;
    SELECT count(*) INTO active_count FROM doctors WHERE on_call;
    IF active_count <= 1 THEN
        RETURN false;
    END IF;

    UPDATE doctors
    SET on_call = false
    WHERE doctor_id = p_doctor_id
      AND on_call;
    GET DIAGNOSTICS changed = ROW_COUNT;
    RETURN changed = 1;
END $$;
