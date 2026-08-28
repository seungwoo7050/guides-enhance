-- [Implementation 1] 두 대표 조회가 사용할 table을 정의합니다.
-- equality 조건, 범위와 정렬, 반환 열, partial 조건을 각각 확인할 수 있는 열만 둡니다.
CREATE TABLE events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id integer NOT NULL,
    created_at timestamptz NOT NULL,
    kind text NOT NULL,
    payload text NOT NULL
);

CREATE TABLE jobs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    status text NOT NULL CHECK (status IN ('PENDING', 'RUNNING', 'DONE')),
    scheduled_at timestamptz NOT NULL,
    payload text NOT NULL
);
