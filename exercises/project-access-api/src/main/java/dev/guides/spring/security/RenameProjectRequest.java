package dev.guides.spring.security;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record RenameProjectRequest(
    @NotBlank @Size(max = 80) String title) {}
