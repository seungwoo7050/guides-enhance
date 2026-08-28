package dev.guides.spring.idempotency;

import java.util.UUID;

public record OperationResult(UUID operationId, long quantity) {}
