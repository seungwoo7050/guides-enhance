-- [Implementation 1] 조직과 사용자를 식별합니다.
-- 조직별 관계를 만들기 전에 organization id와 대소문자를 무시하는 email 유일성을 먼저 고정합니다.
CREATE TABLE organizations (
    id bigint PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE users (
    id bigint PRIMARY KEY,
    email text NOT NULL
);
CREATE UNIQUE INDEX users_email_ci_uq ON users(lower(email));

-- [Implementation 2] membership과 project에 조직 범위를 포함합니다.
-- 복합 key를 두어 이후 foreign key가 애플리케이션 검사 없이도 org_id 불일치를 거부하게 합니다.
CREATE TABLE memberships (
    org_id bigint NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('OWNER', 'MEMBER')),
    PRIMARY KEY (org_id, user_id)
);

CREATE TABLE projects (
    id bigint PRIMARY KEY,
    org_id bigint NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name text NOT NULL CHECK (btrim(name) <> ''),
    UNIQUE (id, org_id),
    UNIQUE (org_id, name)
);

-- [Implementation 3] ticket의 조직 참조와 상태 조합을 제한합니다.
-- project, reporter, assignee가 같은 org_id를 사용하게 하고 status와 closed_at의 허용 조합을 검사합니다.
CREATE TABLE tickets (
    id bigint PRIMARY KEY,
    project_id bigint NOT NULL,
    org_id bigint NOT NULL,
    reporter_id bigint NOT NULL,
    assignee_id bigint,
    title text NOT NULL CHECK (btrim(title) <> ''),
    status text NOT NULL CHECK (status IN ('OPEN', 'IN_PROGRESS', 'DONE')),
    severity text NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    created_at timestamptz NOT NULL,
    closed_at timestamptz,
    FOREIGN KEY (project_id, org_id)
        REFERENCES projects(id, org_id)
        ON DELETE CASCADE,
    FOREIGN KEY (org_id, reporter_id)
        REFERENCES memberships(org_id, user_id),
    FOREIGN KEY (org_id, assignee_id)
        REFERENCES memberships(org_id, user_id),
    CHECK (
        (status = 'DONE' AND closed_at IS NOT NULL)
        OR
        (status <> 'DONE' AND closed_at IS NULL)
    )
);
