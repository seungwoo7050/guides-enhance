package dev.guides.spring.publication;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.net.URI;

public record CreatePublicationRequest(
    @NotBlank @Size(max = 120) String title,
    @NotNull URI source) {}
