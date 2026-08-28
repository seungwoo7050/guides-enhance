-- [Implementation 7] 대표 조회에 맞는 index를 추가합니다.
-- 각 partial composite index의 조건과 key 순서를 실제 WHERE와 ORDER BY에 맞춥니다.

-- [Implementation 7-1] 조직별 내림차순 keyset 조회 index를 추가합니다.
CREATE INDEX IF NOT EXISTS tickets_org_open_priority_created_idx
ON tickets(org_id, priority DESC, created_at DESC, id DESC)
WHERE status <> 'DONE';

-- [Implementation 7-2] project별 backlog 조회 index를 추가합니다.
CREATE INDEX IF NOT EXISTS tickets_project_open_created_idx
ON tickets(org_id, project_id, created_at, id)
WHERE status <> 'DONE';

-- [Implementation 7-3] 담당자별 우선순위 queue index를 추가합니다.
CREATE INDEX IF NOT EXISTS tickets_assignee_queue_idx
ON tickets(org_id, assignee_id, priority DESC, created_at, id)
WHERE status <> 'DONE'
  AND assignee_id IS NOT NULL;
