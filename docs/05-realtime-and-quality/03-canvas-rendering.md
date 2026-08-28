# Canvas 렌더링

`<canvas>`에 그린 픽셀은 애플리케이션 데이터가 아닙니다. 화면이 지워지거나 크기가 바뀌어도 다시 그릴 수 있도록 항목과 선택 상태를 별도 값으로 보관해야 합니다. React는 상태와 수명을 관리하고 Canvas 함수는 그 값을 픽셀로 그리는 역할만 맡는 편이 안전합니다.

## 목표

- 보드 좌표, CSS 픽셀과 장치 픽셀을 구분합니다.
- 저장된 상태만으로 화면 전체를 다시 그립니다.
- React와 명령형 Canvas 코드를 연결합니다.
- 포인터 좌표를 보드 좌표로 바꾸고 서버에서도 범위를 검사합니다.
- 측정 뒤 필요한 최적화만 적용하고 키보드 사용 경로를 제공합니다.

## 픽셀을 상태로 사용하지 않습니다

```ts
interface BoardViewState {
  items: BoardItem[];
  cursors: RemoteCursor[];
  selection: string | null;
  viewport: Viewport;
}
```

렌더러는 이 값을 읽어 그립니다.

```ts
function renderBoard(ctx: CanvasRenderingContext2D, state: BoardViewState): void {
  ctx.clearRect(0, 0, state.viewport.width, state.viewport.height);
  for (const item of state.items) drawItem(ctx, item);
  for (const cursor of state.cursors) drawCursor(ctx, cursor);
  if (state.selection) drawSelection(ctx, state.selection, state.items);
}
```

Canvas 픽셀을 읽어 항목 데이터를 복원하지 않습니다. 재연결 뒤 스냅샷을 받아도 같은 상태만으로 전체를 다시 그릴 수 있어야 합니다.

## 세 좌표계

1. 보드 좌표: 서버와 데이터베이스에 저장할 논리 좌표
2. CSS 픽셀: 화면에서 보이는 Canvas 크기
3. 장치 픽셀: 실제 백킹 버퍼 해상도

고밀도 화면에서 선명하게 그리려면 CSS 크기와 버퍼 크기를 나눕니다.

```ts
function resizeCanvas(
  canvas: HTMLCanvasElement,
  width: number,
  height: number
): CanvasRenderingContext2D {
  const ratio = window.devicePixelRatio || 1;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);

  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("2D Canvas를 사용할 수 없습니다.");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return ctx;
}
```

크기를 바꿀 때마다 `scale()`을 누적 호출하지 않고 `setTransform()`으로 기준 변환을 다시 설정합니다.

## 포인터 좌표 변환

```ts
function pointerToBoard(
  event: PointerEvent,
  canvas: HTMLCanvasElement,
  view: Viewport
) {
  const rect = canvas.getBoundingClientRect();
  const cssX = event.clientX - rect.left;
  const cssY = event.clientY - rect.top;
  return {
    x: (cssX - view.offsetX) / view.zoom,
    y: (cssY - view.offsetY) / view.zoom
  };
}
```

스크롤, 확대·축소와 보드 이동을 모두 반영합니다. 브라우저가 계산한 좌표는 수정할 수 있으므로 서버도 유한한 숫자인지와 허용 범위를 다시 검사합니다.

## React와 연결

```tsx
function BoardCanvas({ state }: { state: BoardViewState }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useLayoutEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = resizeCanvas(canvas, state.viewport.width, state.viewport.height);
    renderBoard(ctx, state);
  }, [state]);

  return <canvas ref={ref} aria-label="협업 보드" />;
}
```

먼저 상태가 바뀔 때 전체를 다시 그리는 단순한 방식으로 구현합니다. 실제로 프레임 시간이 부족한 것이 확인된 뒤 변경 영역 다시 그리기, 오프스크린 Canvas와 공간 인덱스를 검토합니다.

## 애니메이션

```ts
let frame = 0;
function tick(time: number) {
  renderInterpolated(time);
  frame = requestAnimationFrame(tick);
}
frame = requestAnimationFrame(tick);
```

화면이 사라질 때 `cancelAnimationFrame(frame)`을 호출합니다. 여러 Effect가 각각 루프를 시작하지 않게 합니다. 백그라운드 탭에서는 프레임 빈도가 낮아질 수 있으므로 경기 시간이나 서버 타임아웃을 프레임 수로 계산하지 않습니다.

## 적중 판정

```text
화면 좌표를 보드 좌표로 변환
→ 후보 항목 찾기
→ 도형별 포함 여부 확인
→ 가장 위에 있는 항목 선택
```

항목이 적을 때는 뒤에서부터 순회해도 충분합니다. 항목 수가 늘고 측정 결과가 필요성을 보여 줄 때 공간 인덱스를 도입합니다.

## 텍스트 입력

Canvas 안에서 텍스트 입력을 직접 구현하면 IME, 선택, 클립보드와 접근성을 모두 다시 만들어야 합니다. 입력할 때는 Canvas 위에 HTML `input`이나 `textarea`를 겹쳐 두는 편이 적합할 수 있습니다.

```text
Canvas → 배경, 도형, 선택 표시
DOM    → 폼, 메뉴, 대화 상자, 텍스트 입력, 상태 안내
```

## 접근성

Canvas 픽셀만으로는 스크린 리더가 항목을 읽기 어렵습니다.

- Canvas 목적을 설명하는 이름
- 항목과 선택 상태를 보여 주는 DOM 목록
- 키보드로 선택·이동·삭제할 방법
- 색 외의 상태 표시
- 저장·충돌 상태를 알리는 `status` 또는 `alert`
- 동작 줄이기 설정 반영

## 이미지와 보안

외부 이미지를 그리면 CORS 설정에 따라 픽셀 읽기와 내보내기가 막힐 수 있습니다. 업로드 이미지는 크기, 형식과 디코딩 실패를 제한합니다. 실행 가능한 SVG나 HTML을 검증 없이 삽입하지 않습니다.

## 성능 확인

- 한 프레임을 그리는 시간
- 항목 수에 따른 처리 시간
- 포인터 이벤트 빈도
- React 렌더링과 Canvas 그리기 시간
- 백킹 버퍼 메모리
- 원격 커서 메시지 빈도

측정 전부터 복잡한 최적화를 도입하지 않습니다.

## 흔한 실수

- Canvas 픽셀을 애플리케이션 데이터로 사용합니다.
- CSS 크기와 장치 픽셀 크기를 같게 둡니다.
- 크기 변경 때 변환을 계속 누적합니다.
- 브라우저 좌표를 서버가 그대로 저장합니다.
- 애니메이션과 이벤트 리스너를 정리하지 않습니다.
- 모든 폼과 텍스트 입력을 Canvas에 구현합니다.
- 측정하기 전에 부분 다시 그리기부터 만듭니다.

## 완료 기준

- 보드·CSS·장치 좌표를 구분하고 변환합니다.
- 저장된 상태만으로 전체 Canvas를 다시 그립니다.
- Effect, 애니메이션과 리스너를 정리합니다.
- 브라우저 적중 판정과 서버 좌표 검사를 모두 수행합니다.
- Canvas 밖에 키보드와 보조 기술이 사용할 UI를 제공합니다.

## 연결 exercise

현재 competency suite에는 Canvas 전용 exercise가 없습니다. 실제 프로젝트의 게임 화면을 구현할 때 이 문서를 JIT로 사용하고, 상태 관리와 실시간 전송은 [`realtime-board`](../../exercises/realtime-board/README.md)로 다시 확인합니다.
