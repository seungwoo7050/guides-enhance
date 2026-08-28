# CSS 레이아웃과 반응형 화면

반응형 화면은 기기 이름별로 미디어 쿼리를 많이 추가하는 방식으로 만들지 않습니다. 요소가 사용할 수 있는 공간만큼 줄어들고, 긴 콘텐츠가 넘치지 않으며, 실제로 배치가 깨지는 지점에서만 열과 행을 바꾸는 방식으로 만듭니다.

이 문서는 화면 배치를 구현하기 직전에 읽는 JIT 문서입니다.

## 목표

- 캐스케이드와 박스 모델을 이해합니다.
- 일반 문서 흐름, Flexbox, Grid를 상황에 맞게 선택합니다.
- 요소가 작은 화면에서도 줄어들도록 최소 크기를 조정합니다.
- 긴 문자열, 320px 화면, 200% 확대에서 확인합니다.
- 포커스 표시와 사용자 모션 설정을 보존합니다.

## 박스 크기

```css
*, *::before, *::after {
  box-sizing: border-box;
}
```

`border-box`를 사용하면 선언한 너비 안에 `padding`과 `border`가 포함됩니다. `width: 100%`인 입력 요소가 컨테이너 밖으로 넘는 문제를 줄일 수 있습니다.

## 일반 흐름부터 사용합니다

블록 요소는 문서 순서대로 쌓이고 텍스트는 사용 가능한 너비에서 줄바꿈됩니다. 먼저 일반 흐름으로 읽을 수 있는 화면을 만든 뒤 정렬이 필요한 부분에만 Flexbox나 Grid를 적용합니다.

모든 요소를 절대 위치로 배치하면 콘텐츠 길이, 글자 확대, 번역에 대응하기 어렵습니다.

## Flexbox와 Grid

한 방향으로 배치하고 정렬할 때는 Flexbox가 적합합니다.

```css
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .75rem;
}
```

반복되는 카드처럼 행과 열이 필요한 경우에는 Grid를 사용할 수 있습니다.

```css
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
  gap: 1rem;
}
```

`min(100%, 18rem)`은 작은 화면에서 열의 최소 너비가 컨테이너보다 커지는 일을 막습니다.

## 줄어들지 않는 요소 처리

Flexbox와 Grid의 자식은 콘텐츠의 최소 너비 때문에 예상보다 줄어들지 않을 수 있습니다.

```css
.card-title {
  min-width: 0;
  overflow-wrap: anywhere;
}
```

공백 없는 긴 URL이나 사용자가 입력한 긴 제목으로 확인합니다. 보기 좋은 짧은 샘플만 사용하면 실제 넘침을 발견하기 어렵습니다.

## 유연한 너비

```css
main {
  width: min(70rem, calc(100% - 2rem));
  margin-inline: auto;
}
```

읽기 편한 최대 너비는 제한하되, 화면보다 넓어지지 않게 합니다. `rem`은 사용자의 글자 크기 설정을 반영하기 쉽습니다.

```css
.form-row {
  display: flex;
  gap: .5rem;
}

.form-row input {
  min-width: 0;
  flex: 1;
}

@media (max-width: 30rem) {
  .form-row { flex-direction: column; }
}
```

브레이크포인트는 특정 휴대전화 모델이 아니라 실제 배치가 읽기 어려워지는 너비에서 정합니다.

## 확인할 조건

최소한 다음 상황을 직접 확인합니다.

- CSS 픽셀 기준 너비 320px
- 브라우저 확대 200%
- 긴 제목과 빈 목록
- 시스템 글자 크기 증가
- 포커스 윤곽선이 잘리지 않는지
- 가로 스크롤이 필요한 Canvas나 표를 제외한 페이지 전체에서 의도하지 않은 가로 스크롤이 생기지 않는지

간단한 자동 검사도 사용할 수 있습니다.

```js
document.documentElement.scrollWidth <= document.documentElement.clientWidth
```

이 조건만으로 디자인을 평가할 수는 없지만 페이지 전체의 가로 넘침은 찾을 수 있습니다.

## 색상과 모션

상태를 색만으로 구분하지 않습니다. 텍스트나 아이콘의 접근 가능한 이름을 함께 제공합니다. 애니메이션이 꼭 필요하지 않다면 사용자의 동작 줄이기 설정을 존중합니다.

```css
@media (prefers-reduced-motion: reduce) {
  .animated {
    animation: none;
    transition: none;
  }
}
```

전역에서 모든 시간을 강제로 바꾸기보다 실제 애니메이션 요소에 적용합니다.

## 흔한 실수

- 모든 너비를 고정 픽셀로 지정합니다.
- `100vw`가 스크롤바 너비까지 포함할 수 있다는 점을 놓칩니다.
- 긴 문자열과 화면 확대를 확인하지 않습니다.
- CSS `order`로 보이는 순서만 바꾸고 키보드 이동 순서는 그대로 둡니다.
- `overflow: hidden`으로 포커스 윤곽선을 잘라 냅니다.

## 관련 exercise

[`browser-directory`](../../exercises/browser-directory/README.md)는 작은 화면의 검색 폼, 긴 결과 텍스트와 포커스 표시를 검사합니다.

## 완료 기준

- `content-box`와 `border-box`의 차이를 설명할 수 있습니다.
- Flexbox와 Grid 중 하나를 선택한 이유를 설명할 수 있습니다.
- 긴 콘텐츠와 작은 화면에서도 필요한 요소를 사용할 수 있습니다.
- 화면 확대와 키보드 포커스 때문에 기능이 가려지지 않습니다.
