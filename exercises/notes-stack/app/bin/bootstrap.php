<?php
declare(strict_types=1);

// [Implementation 4] Validate bootstrap settings and the secret file
function requiredEnv(string $name): string {
    $value = getenv($name);
    if ($value === false || $value === '') {
        throw new RuntimeException("{$name} 환경변수가 필요합니다.");
    }
    return $value;
}

function readSecret(string $path): string {
    $value = @file_get_contents($path);
    if ($value === false) {
        throw new RuntimeException("비밀값 파일을 읽을 수 없습니다: {$path}");
    }

    $value = preg_replace('/\r?\n\z/', '', $value) ?? '';
    if ($value === '' || str_contains($value, "\r") || str_contains($value, "\n")) {
        throw new RuntimeException("비밀값 파일은 비어 있지 않은 한 줄이어야 합니다: {$path}");
    }
    return $value;
}

function runBootstrap(): void {
    $host = requiredEnv('DB_HOST');
    $name = requiredEnv('DB_NAME');
    $user = requiredEnv('DB_USER');
    $password = readSecret(requiredEnv('DB_PASSWORD_FILE'));
    $dsn = "mysql:host={$host};dbname={$name};charset=utf8mb4";

    $maxAttempts = (int)(getenv('DB_CONNECT_ATTEMPTS') ?: '60');
    $delayMs = (int)(getenv('DB_CONNECT_DELAY_MS') ?: '500');
    if ($maxAttempts < 1 || $maxAttempts > 600 || $delayMs < 0 || $delayMs > 10_000) {
        throw new RuntimeException('데이터베이스 재시도 설정이 올바르지 않습니다.');
    }

    // [Implementation 4-1] Retry the PDO connection within a fixed limit
    $pdo = null;
    $lastError = null;
    for ($attempt = 1; $attempt <= $maxAttempts; $attempt++) {
        try {
            $pdo = new PDO($dsn, $user, $password, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
            ]);
            break;
        } catch (PDOException $error) {
            $lastError = $error;
            if ($attempt < $maxAttempts) {
                usleep($delayMs * 1000);
            }
        }
    }

    if (!$pdo instanceof PDO) {
        throw new RuntimeException(
            sprintf('데이터베이스가 %d회 안에 준비되지 않았습니다.', $maxAttempts),
            0,
            $lastError
        );
    }

    // [Implementation 4-2] Create the application tables when absent
    $pdo->exec(<<<'SQL'
CREATE TABLE IF NOT EXISTS app_meta (
    meta_key VARCHAR(100) PRIMARY KEY,
    meta_value VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
SQL);
    $pdo->exec(<<<'SQL'
CREATE TABLE IF NOT EXISTS notes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    body VARCHAR(500) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
SQL);

    // [Implementation 4-3] Insert the seed marker and note in one transaction
    // 마커와 최초 메모는 함께 커밋되어야 합니다. 메모 삽입이 실패했는데 마커만
    // 남으면 다음 시작에서 최초 데이터를 다시 넣을 수 없습니다.
    $pdo->beginTransaction();
    try {
        $marker = $pdo->prepare(
            "INSERT IGNORE INTO app_meta (meta_key, meta_value) VALUES ('seed_v1', 'done')"
        );
        $marker->execute();

        if ($marker->rowCount() === 1) {
            $seed = $pdo->prepare('INSERT INTO notes (body) VALUES (:body)');
            $seed->execute(['body' => 'seed note']);
            fwrite(STDERR, "최초 메모를 추가했습니다.\n");
        } else {
            fwrite(STDERR, "최초 메모가 이미 있어 건너뜁니다.\n");
        }
        $pdo->commit();
    } catch (Throwable $error) {
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
        throw $error;
    }
}

try {
    runBootstrap();
} catch (Throwable $error) {
    $message = $error instanceof RuntimeException
        ? $error->getMessage()
        : '예상하지 못한 오류가 발생했습니다.';
    fwrite(STDERR, "애플리케이션 초기화에 실패했습니다: {$message}\n");
    exit(1);
}
