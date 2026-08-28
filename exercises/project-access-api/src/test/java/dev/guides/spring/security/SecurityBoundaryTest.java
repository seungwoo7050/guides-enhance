package dev.guides.spring.security;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
class SecurityBoundaryTest {
  @Autowired private MockMvc mvc;
  @Autowired private ProjectStore projects;

  @BeforeEach
  void resetProject() {
    projects.reset();
  }

  @Test
  void authenticationIsRequired() throws Exception {
    mvc.perform(get("/api/projects/1"))
        .andExpect(status().isUnauthorized())
        .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
        .andExpect(jsonPath("$.errorCode").value("AUTHENTICATION_REQUIRED"));
  }

  @Test
  void authenticatedNonOwnerCannotRename() throws Exception {
    mvc.perform(post("/api/projects/1/rename")
            .with(httpBasic("viewer", "viewer-password"))
            .with(csrf())
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"title\":\"Viewer update\"}"))
        .andExpect(status().isForbidden())
        .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON))
        .andExpect(jsonPath("$.errorCode").value("ACCESS_DENIED"));
  }

  @Test
  void csrfTokenIsRequiredForStateChange() throws Exception {
    mvc.perform(post("/api/projects/1/rename")
            .with(httpBasic("owner", "owner-password"))
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"title\":\"Update without CSRF\"}"))
        .andExpect(status().isForbidden())
        .andExpect(jsonPath("$.errorCode").value("ACCESS_DENIED"));
  }

  @Test
  void ownerWithCsrfCanRename() throws Exception {
    mvc.perform(post("/api/projects/1/rename")
            .with(httpBasic("owner", "owner-password"))
            .with(csrf())
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"title\":\"Updated title\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.owner").value("owner"))
        .andExpect(jsonPath("$.title").value("Updated title"));
  }

  @Test
  void blankTitleIsRejectedAtMvcBoundary() throws Exception {
    mvc.perform(post("/api/projects/1/rename")
            .with(httpBasic("owner", "owner-password"))
            .with(csrf())
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"title\":\"   \"}"))
        .andExpect(status().isBadRequest());
  }
}
