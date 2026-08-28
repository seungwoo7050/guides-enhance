package dev.guides.spring.security;

import org.springframework.stereotype.Component;

@Component("projectAccess")
public final class ProjectAccess {
  private final ProjectStore projects;

  public ProjectAccess(ProjectStore projects) {
    this.projects = projects;
  }

  // [Implementation 2] 인증 사용자와 프로젝트 소유자 비교
  // URL 접근 허용과 별개로 저장된 객체의 소유자를 확인합니다.
  public boolean canEdit(long projectId, String username) {
    return projects.isOwner(projectId, username);
  }
}
