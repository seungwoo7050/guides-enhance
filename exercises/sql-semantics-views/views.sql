-- [Implementation 2] NULL에 안전하게 주문 없는 사용자를 찾습니다.
-- 상관 NOT EXISTS를 사용해 하위 결과의 NULL이 바깥 사용자를 제거하지 않게 합니다.
CREATE VIEW q01_users_without_orders AS
SELECT u.id, u.email
FROM users AS u
WHERE NOT EXISTS (
    SELECT 1
    FROM orders AS o
    WHERE o.user_id = u.id
);

-- [Implementation 3] NULL에 안전하게 차단되지 않은 사용자를 찾습니다.
-- blocked_users에 NULL이 있어도 실제로 차단된 사용자만 제외합니다.
CREATE VIEW q02_unblocked_users AS
SELECT u.id, u.email
FROM users AS u
WHERE NOT EXISTS (
    SELECT 1
    FROM blocked_users AS b
    WHERE b.user_id = u.id
);

-- [Implementation 4] 사용자별 주문 수와 합계를 계산합니다.
-- users를 기준으로 LEFT JOIN하고, COUNT(o.id)와 COALESCE로 주문 없는 사용자도 0으로 남깁니다.
CREATE VIEW q03_user_totals AS
SELECT
    u.id,
    count(o.id)::integer AS order_count,
    coalesce(sum(o.total_cents), 0)::bigint AS total_cents
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id
GROUP BY u.id;

-- [Implementation 5] 동률까지 순서가 고정된 지출 순위를 만듭니다.
-- 합계가 같으면 id 오름차순으로 순서를 정하고 position을 조회 결과에 포함합니다.
CREATE VIEW q04_ranked_spenders AS
SELECT id, order_count, total_cents, position
FROM (
    SELECT
        id,
        order_count,
        total_cents,
        row_number() OVER (ORDER BY total_cents DESC, id ASC)::integer AS position
    FROM q03_user_totals
) AS ranked
WHERE position <= 3;
