package dev.guides.spring.publication;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.net.URI;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/publications")
public final class PublicationController {
  private final PublicationService service;

  public PublicationController(PublicationService service) {
    this.service = service;
  }

  // [Implementation 8] 인증 사용자와 멱등성 key를 생성 요청에 연결
  // 새로 만들면 201, 기존 결과를 반환하면 200으로 응답합니다.
  @PostMapping
  public ResponseEntity<PublicationResponse> create(
      Authentication authentication,
      @RequestHeader("Idempotency-Key")
          @NotBlank @Size(max = 120) String idempotencyKey,
      @Valid @RequestBody CreatePublicationRequest request) {
    PublicationResult result = service.create(
        authentication.getName(),
        idempotencyKey,
        request);
    if (result.created()) {
      return ResponseEntity
          .created(URI.create("/api/publications/" + result.response().id()))
          .body(result.response());
    }
    return ResponseEntity.ok(result.response());
  }
}
