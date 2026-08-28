package dev.guides.spring.publication;

import java.net.URI;
import java.util.UUID;

public record PublicationResponse(
    UUID id,
    String actorId,
    String title,
    URI source) {}
