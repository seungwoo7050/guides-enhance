-- [Implementation 1] 관계와 제약을 정의합니다.
-- NULL, 외부 조인, 집계, 정렬 순서를 각각 관찰할 수 있는 table만 둡니다.
CREATE TABLE users (
    id integer PRIMARY KEY,
    email text NOT NULL UNIQUE
);

CREATE TABLE orders (
    id integer PRIMARY KEY,
    user_id integer NOT NULL REFERENCES users(id),
    total_cents integer NOT NULL CHECK (total_cents >= 0)
);

CREATE TABLE blocked_users (
    user_id integer REFERENCES users(id)
);
