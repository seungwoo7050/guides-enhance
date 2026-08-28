<?php
declare(strict_types=1);

function envRequired(string $name): string {
    $value = getenv($name);
    if ($value === false || $value === '') {
        throw new RuntimeException("{$name} 환경변수가 필요합니다.");
    }
    return $value;
}

function readRuntimeSecret(string $path): string {
    $value = @file_get_contents($path);
    if ($value === false) {
        throw new RuntimeException('비밀값 파일을 읽을 수 없습니다.');
    }

    $value = preg_replace('/\r?\n\z/', '', $value) ?? '';
    if ($value === '' || str_contains($value, "\r") || str_contains($value, "\n")) {
        throw new RuntimeException('비밀값 파일 형식이 올바르지 않습니다.');
    }
    return $value;
}

// [Implementation 6] Reuse one PDO connection in each PHP-FPM worker
function db(): PDO {
    // 이 값은 PHP-FPM 워커 하나의 수명 동안만 재사용합니다.
    // 실행 중 끊어진 연결을 자동으로 다시 만드는 기능은 포함하지 않습니다.
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }

    $dsn = sprintf(
        'mysql:host=%s;dbname=%s;charset=utf8mb4',
        envRequired('DB_HOST'),
        envRequired('DB_NAME')
    );
    $pdo = new PDO(
        $dsn,
        envRequired('DB_USER'),
        readRuntimeSecret(envRequired('DB_PASSWORD_FILE')),
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]
    );
    return $pdo;
}

function jsonResponse(array $payload, int $status = 200): never {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
    exit;
}

// [Implementation 6-1] Route note requests and validate request bodies
try {
    $path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
    $method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

    if ($path === '/health') {
        db()->query('SELECT 1')->fetchColumn();
        jsonResponse(['status' => 'ok', 'database' => 'ok']);
    }

    if ($path === '/api/notes' && $method === 'GET') {
        $rows = db()->query('SELECT id, body, created_at FROM notes ORDER BY id')->fetchAll();
        jsonResponse(['notes' => $rows]);
    }

    if ($path === '/api/notes' && $method === 'POST') {
        $input = json_decode(
            file_get_contents('php://input') ?: '{}',
            true,
            512,
            JSON_THROW_ON_ERROR
        );
        $body = trim((string)($input['body'] ?? ''));
        if ($body === '' || strlen($body) > 500) {
            jsonResponse(['error' => '본문은 1~500바이트여야 합니다.'], 400);
        }

        $statement = db()->prepare('INSERT INTO notes (body) VALUES (:body)');
        $statement->execute(['body' => $body]);
        jsonResponse(['id' => (int)db()->lastInsertId(), 'body' => $body], 201);
    }

    if ($path !== '/') {
        jsonResponse(['error' => 'not_found'], 404);
    }

    $count = (int)db()->query('SELECT COUNT(*) FROM notes')->fetchColumn();
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><meta charset="utf-8"><title>Notes Stack</title>';
    echo '<h1>Notes Stack</h1><p>저장된 메모: ' . $count . '</p>';
} catch (JsonException) {
    jsonResponse(['error' => 'invalid_json'], 400);
} catch (Throwable $error) {
    error_log('요청 처리 실패: ' . $error::class);
    jsonResponse(['error' => 'internal_server_error'], 500);
}
