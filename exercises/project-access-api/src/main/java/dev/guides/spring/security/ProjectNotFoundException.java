package dev.guides.spring.security;

public final class ProjectNotFoundException extends RuntimeException {
  public ProjectNotFoundException(long id) {
    super("Project not found: " + id);
  }
}
