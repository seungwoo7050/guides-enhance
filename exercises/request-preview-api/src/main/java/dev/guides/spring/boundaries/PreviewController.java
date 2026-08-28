package dev.guides.spring.boundaries;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/requests")
public final class PreviewController {
  private final RequestPolicyProperties policy;

  public PreviewController(RequestPolicyProperties policy) {
    this.policy = policy;
  }

  // [Implementation 3] 카테고리와 수량 업무 규칙 검사
  // 형식 검증을 통과한 요청만 설정된 허용값과 비교합니다.
  @PostMapping("/preview")
  public PreviewResponse preview(@Valid @RequestBody PreviewRequest request) {
    if (!policy.category().equals(request.category())) {
      throw new PolicyViolationException("CATEGORY_NOT_SUPPORTED", "The category is not supported.");
    }
    if (request.quantity() < policy.minQuantity() || request.quantity() > policy.maxQuantity()) {
      throw new PolicyViolationException("QUANTITY_OUT_OF_RANGE", "The quantity is outside the allowed range.");
    }
    return new PreviewResponse(request.quantity(), request.category(), true);
  }
}
