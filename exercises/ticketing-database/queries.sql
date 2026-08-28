-- [Implementation 6] 조직 조건과 조회 행의 의미를 view로 고정합니다.
-- index를 정하기 전에 미완료 조건, 집계 단위, keyset cursor 열을 먼저 명시합니다.

-- [Implementation 6-1] project별 미완료 ticket을 집계합니다.
-- 미완료 ticket이 없는 project도 한 행으로 남기고 count와 oldest 시각을 계산합니다.
CREATE OR REPLACE VIEW q_project_backlog AS
SELECT
    p.org_id,
    p.id AS project_id,
    count(t.id) FILTER (WHERE t.status <> 'DONE')::bigint AS open_count,
    min(t.created_at) FILTER (WHERE t.status <> 'DONE') AS oldest_opened_at
FROM projects AS p
LEFT JOIN tickets AS t
  ON t.project_id = p.id
 AND t.org_id = p.org_id
GROUP BY p.org_id, p.id;

-- [Implementation 6-2] 조직별 keyset page에 필요한 행을 제공합니다.
-- (priority, created_at, id) 전체 값을 노출해 동률이 있어도 다음 page가 달라지지 않게 합니다.
CREATE OR REPLACE VIEW q_org_open_tickets AS
SELECT id, org_id, project_id, priority, created_at
FROM tickets
WHERE status <> 'DONE';

-- [Implementation 6-3] 담당자별 미완료 ticket을 제공합니다.
-- assignee가 있고 DONE이 아닌 ticket만 조직별 queue 조회에 포함합니다.
CREATE OR REPLACE VIEW q_assignee_queue AS
SELECT id, org_id, project_id, assignee_id, priority, created_at
FROM tickets
WHERE assignee_id IS NOT NULL
  AND status <> 'DONE';
