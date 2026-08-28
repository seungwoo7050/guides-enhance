-- [Implementation 1-1] planner가 분포를 판단할 수 있는 고정 데이터를 만듭니다.
-- 행 수와 선택도를 일정하게 유지해 index 선택과 결과 순서를 반복해서 확인할 수 있게 합니다.
INSERT INTO events(tenant_id, created_at, kind, payload)
SELECT
    (g % 50) + 1,
    timestamptz '2025-01-01 00:00:00+00' + g * interval '1 second',
    CASE WHEN g % 20 = 0 THEN 'ERROR' ELSE 'INFO' END,
    repeat(md5(g::text), 2)
FROM generate_series(1, 100000) AS g;

INSERT INTO jobs(status, scheduled_at, payload)
SELECT
    CASE WHEN g % 20 = 0 THEN 'PENDING' WHEN g % 3 = 0 THEN 'RUNNING' ELSE 'DONE' END,
    timestamptz '2025-02-01 00:00:00+00' + g * interval '1 minute',
    md5(g::text)
FROM generate_series(1, 50000) AS g;

ANALYZE events;
ANALYZE jobs;
