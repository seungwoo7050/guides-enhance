-- [Implementation 1] 동시 실행용 데이터와 공용 guard row를 준비합니다.
-- 재고는 같은 행에서 충돌하고, 당직 변경 경로는 모두 shift_guard의 같은 행을 잠급니다.
CREATE TABLE inventory (
    sku text PRIMARY KEY,
    available integer NOT NULL CHECK (available >= 0)
);
INSERT INTO inventory(sku, available) VALUES ('book', 10);

CREATE TABLE shift_guard (
    id integer PRIMARY KEY CHECK (id = 1)
);
INSERT INTO shift_guard(id) VALUES (1);

CREATE TABLE doctors (
    doctor_id integer PRIMARY KEY,
    on_call boolean NOT NULL
);
INSERT INTO doctors(doctor_id, on_call) VALUES (1, true), (2, true);
