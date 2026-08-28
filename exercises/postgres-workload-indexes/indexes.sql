-- [Implementation 2] tenant별 최신 event 조회 index를 추가합니다.
-- tenant_id 뒤에 (created_at DESC, id DESC)를 두고 반환 전용 열은 INCLUDE에 넣습니다.
CREATE INDEX events_tenant_created_id_idx
ON events(tenant_id, created_at DESC, id DESC)
INCLUDE (kind, payload);

-- [Implementation 3] 대기 중인 job만 저장하는 partial index를 추가합니다.
-- status가 PENDING인 행만 넣고 key 순서를 scheduled_at, id 조회 순서와 맞춥니다.
CREATE INDEX jobs_pending_schedule_idx
ON jobs(scheduled_at, id)
INCLUDE (payload)
WHERE status = 'PENDING';
