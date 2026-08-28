-- [Implementation 4] priority 열을 추가하고 기존 값을 다시 실행 가능하게 채웁니다.
-- 호환 기간에는 severity를 남겨 두고 NULL인 priority만 변환합니다.
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority integer;

UPDATE tickets
SET priority = CASE severity
    WHEN 'CRITICAL' THEN 5
    WHEN 'HIGH' THEN 4
    WHEN 'MEDIUM' THEN 3
    WHEN 'LOW' THEN 2
END
WHERE priority IS NULL;

-- [Implementation 5] 기존 값을 검증한 뒤 priority를 필수 값으로 바꿉니다.
-- CHECK를 NOT VALID로 추가하고 기존 행을 검증한 다음 NOT NULL을 설정합니다.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'tickets'::regclass
          AND conname = 'tickets_priority_range'
    ) THEN
        EXECUTE 'ALTER TABLE tickets ADD CONSTRAINT tickets_priority_range CHECK (priority BETWEEN 1 AND 5) NOT VALID';
    END IF;
END $$;

ALTER TABLE tickets VALIDATE CONSTRAINT tickets_priority_range;
ALTER TABLE tickets ALTER COLUMN priority SET NOT NULL;
