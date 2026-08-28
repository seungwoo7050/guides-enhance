package dev.guides.spring.boundaries;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

// [Implementation 2] 요청 본문의 형식 검증
// 현재 요청만으로 판단할 수 있는 값 형식은 Controller 호출 전에 거부합니다.
public record PreviewRequest(
    @Min(1) long quantity,
    @NotBlank String category) {}
