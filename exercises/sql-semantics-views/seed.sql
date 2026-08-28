-- [Implementation 1-1] 의미 차이를 드러내는 고정 데이터를 넣습니다.
-- 0원 주문, 주문 없는 사용자, 같은 합계, NULL 차단 항목을 한 데이터셋에 포함합니다.
INSERT INTO users(id, email) VALUES
    (1, 'a@example.test'),
    (2, 'b@example.test'),
    (3, 'c@example.test'),
    (4, 'd@example.test'),
    (5, 'e@example.test');

INSERT INTO orders(id, user_id, total_cents) VALUES
    (10, 1, 5000),
    (11, 1, 0),
    (12, 2, 0),
    (13, 4, 9000),
    (14, 4, 1000);

INSERT INTO blocked_users(user_id) VALUES (2), (NULL);
