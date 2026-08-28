INSERT INTO organizations(id, name) VALUES (1, 'alpha'), (2, 'beta');
INSERT INTO users(id, email) VALUES
    (1, 'owner@alpha.test'),
    (2, 'worker@alpha.test'),
    (3, 'outsider@beta.test');
INSERT INTO memberships(org_id, user_id, role) VALUES
    (1, 1, 'OWNER'),
    (1, 2, 'MEMBER'),
    (2, 3, 'OWNER');
INSERT INTO projects(id, org_id, name) VALUES
    (10, 1, 'api'),
    (20, 2, 'other');
INSERT INTO tickets(
    id,
    project_id,
    org_id,
    reporter_id,
    assignee_id,
    title,
    status,
    severity,
    created_at,
    closed_at
) VALUES
    (100, 10, 1, 1, 2, 'critical open', 'OPEN', 'CRITICAL', '2025-01-01', NULL),
    (101, 10, 1, 1, 2, 'high progress', 'IN_PROGRESS', 'HIGH', '2025-01-02', NULL),
    (102, 10, 1, 2, NULL, 'medium open', 'OPEN', 'MEDIUM', '2025-01-03', NULL),
    (104, 10, 1, 2, NULL, 'same key needs id tie break', 'OPEN', 'MEDIUM', '2025-01-03', NULL),
    (103, 10, 1, 1, 2, 'closed low', 'DONE', 'LOW', '2025-01-01', '2025-01-04'),
    (200, 20, 2, 3, 3, 'other org', 'OPEN', 'HIGH', '2025-01-01', NULL);
