# Canvas 렌더링

`<canvas>`는 현재 화면에 픽셀을 그리는 **명령형 렌더링 표면**입니다. Canvas에 그려진 픽셀 자체에는 "이 사각형이 어떤 항목인지", "현재 선택된 항목이 무엇인지" 같은 애플리케이션 의미가 남아 있지 않습니다.

따라서 Canvas 픽셀을 상태로 취급하지 않고, 다시 그리는 데 필요한 데이터를 별도로 보관해야 합니다.

```text
애플리케이션 상태
        ↓
Canvas 렌더러
        ↓
현재 화면의 픽셀
```

Canvas가 지워지거나 크기가 바뀌거나 브라우저가 다시 연결되어도, 저장된 상태만 있으면 화면 전체를 다시 만들 수 있어야 합니다.

React를 사용하는 경우 역할을 다음처럼 나누면 구조가 명확합니다.

```text
React
→ 상태, 컴포넌트 수명, DOM UI 관리

Canvas 렌더러
→ 전달받은 상태를 픽셀로 그림

서버
→ 공유 상태의 최종 검증과 저장
```

## 목표

- 보드 좌표, CSS 픽셀과 장치 픽셀을 구분합니다.
- 보드 좌표와 화면 좌표 사이의 정방향·역방향 변환을 일관되게 사용합니다.
- 저장된 상태만으로 Canvas 전체를 다시 그립니다.
- React의 선언적 상태 관리와 명령형 Canvas API를 연결합니다.
- 포인터 좌표를 보드 좌표로 바꾸고 서버에서도 다시 검증합니다.
- 드래그, 애니메이션과 이벤트 리스너의 수명을 정리합니다.
- 측정 뒤 필요한 최적화만 적용합니다.
- Canvas만으로 접근 가능한 UI를 대신하려 하지 않고 키보드와 보조 기술용 DOM 경로를 제공합니다.

## 픽셀을 상태로 사용하지 않습니다

보드를 그리는 데 필요한 값은 Canvas 밖에 둡니다.

```ts
interface BoardViewState {
  items: BoardItem[];
  cursors: RemoteCursor[];
  selection: string | null;
  viewport: Viewport;
}
```

예를 들어 `Viewport`를 다음 의미로 정의했다고 가정합니다.

```ts
interface Viewport {
  width: number;   // Canvas의 논리적 CSS 너비
  height: number;  // Canvas의 논리적 CSS 높이
  offsetX: number; // 보드 원점의 CSS 픽셀 x 위치
  offsetY: number; // 보드 원점의 CSS 픽셀 y 위치
  zoom: number;    // 보드 좌표 1단위를 몇 CSS 픽셀로 표시할지
}
```

이 정의에서는 보드 좌표 `(x, y)`를 CSS 좌표로 바꾸는 식이 다음과 같습니다.

```text
cssX = x * zoom + offsetX
cssY = y * zoom + offsetY
```

렌더러는 상태를 읽어 화면을 만듭니다.

```ts
function renderBoard(
  ctx: CanvasRenderingContext2D,
  state: BoardViewState
): void {
  const { viewport } = state;

  // resize 단계에서 설정한 devicePixelRatio 변환은 유지됩니다.
  ctx.clearRect(0, 0, viewport.width, viewport.height);

  ctx.save();

  // 이제 drawItem 등이 보드 좌표를 그대로 사용할 수 있습니다.
  ctx.translate(viewport.offsetX, viewport.offsetY);
  ctx.scale(viewport.zoom, viewport.zoom);

  for (const item of state.items) {
    drawItem(ctx, item);
  }

  for (const cursor of state.cursors) {
    drawCursor(ctx, cursor);
  }

  if (state.selection) {
    drawSelection(ctx, state.selection, state.items);
  }

  ctx.restore();
}
```

여기서 `drawItem()`이 받는 좌표는 서버와 애플리케이션에서 사용하는 **보드 좌표**라고 가정합니다. 확대·축소와 화면 이동은 렌더러의 transform이 담당합니다.

이 구조의 중요한 성질은 다음과 같습니다.

```text
Canvas를 완전히 지움
→ 같은 BoardViewState로 다시 renderBoard()
→ 같은 논리 화면을 복원 가능
```

Canvas 픽셀을 `getImageData()`로 읽어 항목의 위치나 종류를 복원하는 구조로 만들지 않습니다.

재연결 뒤 최신 스냅샷을 받았을 때도 그 상태만으로 화면 전체를 다시 그릴 수 있어야 합니다.

## 세 좌표계

Canvas를 다룰 때는 최소한 세 좌표계를 구분해야 합니다.

### 1. 보드 좌표

애플리케이션에서 사용하는 논리 좌표입니다.

```text
item.x = 120
item.y = 80
```

서버와 데이터베이스에는 보통 이 좌표를 저장합니다.

보드 좌표는 사용자의 모니터 해상도나 `devicePixelRatio`에 의존해서는 안 됩니다.

### 2. CSS 픽셀

브라우저 레이아웃에서 보이는 Canvas의 크기와 포인터 위치에 사용하는 좌표입니다.

예:

```css
canvas {
  width: 800px;
  height: 600px;
}
```

화면 이동과 확대를 적용한 뒤 보드 항목이 실제로 보이는 위치도 먼저 CSS 픽셀 단위로 생각할 수 있습니다.

### 3. 장치 픽셀

Canvas 내부의 **백킹 버퍼(backing buffer)**를 구성하는 실제 픽셀입니다.

예를 들어:

```text
CSS 크기          800 × 600
devicePixelRatio  2
백킹 버퍼        1600 × 1200
```

고밀도 화면에서 CSS 크기와 백킹 버퍼 크기를 동일하게 두면 브라우저가 작은 버퍼를 확대해서 표시하므로 선과 텍스트가 흐릿해질 수 있습니다.

정리하면:

```text
보드 좌표
→ viewport 변환
→ CSS 픽셀
→ devicePixelRatio
→ 장치 픽셀
```

사용자 입력에서는 이 과정을 반대로 수행합니다.

```text
포인터의 CSS 픽셀
→ viewport 역변환
→ 보드 좌표
```

## 고밀도 화면과 백킹 버퍼

고밀도 화면에서 선명하게 그리려면 CSS 크기와 Canvas 내부 버퍼 크기를 분리합니다.

```ts
function resizeCanvas(
  canvas: HTMLCanvasElement,
  width: number,
  height: number
): CanvasRenderingContext2D {
  const ratio = window.devicePixelRatio || 1;

  const pixelWidth = Math.max(1, Math.round(width * ratio));
  const pixelHeight = Math.max(1, Math.round(height * ratio));

  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;

  if (
    canvas.width !== pixelWidth ||
    canvas.height !== pixelHeight
  ) {
    canvas.width = pixelWidth;
    canvas.height = pixelHeight;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("2D Canvas를 사용할 수 없습니다.");
  }

  // 이후 Canvas API에서는 CSS 픽셀 단위로 그릴 수 있게 기준 변환을 설정합니다.
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);

  return ctx;
}
```

`canvas.width`와 `canvas.height`는 CSS 크기가 아니라 백킹 버퍼의 크기입니다.

또한 이 속성에 값을 다시 할당하면 Canvas 내용이 지워지고 2D 컨텍스트의 여러 그리기 상태도 초기화됩니다. 따라서 크기를 설정한 뒤 필요한 transform, 선 스타일, 글꼴 등을 다시 설정해야 합니다.

크기가 변할 때 다음처럼 `scale()`을 계속 호출하면 변환이 누적될 수 있습니다.

```ts
ctx.scale(ratio, ratio);
ctx.scale(ratio, ratio);
ctx.scale(ratio, ratio);
```

대신 기준 변환을 명시적으로 덮어쓰는 `setTransform()`을 사용하면 현재 상태를 예측하기 쉽습니다.

```ts
ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
```

### 매우 큰 백킹 버퍼

백킹 버퍼 메모리는 대략 픽셀 수에 비례합니다.

예를 들어 DPR이 커질수록:

```text
width × height × DPR²
```

에 비례해 픽셀 수가 증가합니다.

따라서 매우 큰 Canvas, 높은 DPR, 여러 오프스크린 버퍼를 함께 사용하면 메모리 사용량이 빠르게 증가할 수 있습니다.

성능 문제가 실제로 확인된다면 서비스 요구에 맞춰 렌더링 해상도 상한을 검토할 수 있습니다. 다만 처음부터 임의로 DPR을 낮추기보다 실제 기기와 메모리 사용량을 측정한 뒤 결정합니다.

## 보드 좌표와 CSS 좌표 변환

좌표 변환은 렌더링과 입력에서 반드시 서로 역함수가 되어야 합니다.

앞에서 정의한 `Viewport`에서는 보드 좌표를 CSS 좌표로 다음처럼 변환할 수 있습니다.

```ts
function boardToCss(
  x: number,
  y: number,
  view: Viewport
) {
  return {
    x: x * view.zoom + view.offsetX,
    y: y * view.zoom + view.offsetY
  };
}
```

반대로 CSS 좌표를 보드 좌표로 바꾸면:

```ts
function cssToBoard(
  cssX: number,
  cssY: number,
  view: Viewport
) {
  return {
    x: (cssX - view.offsetX) / view.zoom,
    y: (cssY - view.offsetY) / view.zoom
  };
}
```

두 식이 서로 정확히 대응해야 합니다.

```text
boardToCss()
    ↕
cssToBoard()
```

렌더링에서는 한 변환을 사용하고 포인터 처리에서는 조금 다른 식을 사용하면 확대·축소할수록 선택 위치가 화면과 어긋날 수 있습니다.

`zoom`은 `0`이나 음수가 되지 않도록 애플리케이션 수준에서 허용 범위를 정합니다.

예:

```ts
const MIN_ZOOM = 0.1;
const MAX_ZOOM = 8;
```

## 포인터 좌표 변환

`PointerEvent.clientX`와 `clientY`는 viewport 기준 CSS 픽셀입니다.

Canvas 내부 CSS 좌표로 바꾸려면 먼저 Canvas의 화면 위치를 뺍니다.

```ts
function pointerToBoard(
  event: PointerEvent,
  canvas: HTMLCanvasElement,
  view: Viewport
) {
  const rect = canvas.getBoundingClientRect();

  const cssX = event.clientX - rect.left;
  const cssY = event.clientY - rect.top;

  return cssToBoard(cssX, cssY, view);
}
```

이 코드는 Canvas의 실제 표시 크기가 `view.width × view.height` CSS 픽셀과 같다는 전제에서는 충분합니다.

### CSS에서 Canvas가 추가로 늘어나거나 줄어드는 경우

반응형 레이아웃이나 CSS transform 때문에 `getBoundingClientRect()`의 크기와 렌더러가 사용하는 논리 크기가 다를 수 있습니다.

예를 들어:

```text
논리 CSS 크기   800 × 600
실제 표시 크기  400 × 300
```

이면 포인터 위치도 논리 크기로 정규화해야 합니다.

```ts
function pointerToBoard(
  event: PointerEvent,
  canvas: HTMLCanvasElement,
  view: Viewport
) {
  const rect = canvas.getBoundingClientRect();

  const cssX =
    (event.clientX - rect.left) *
    (view.width / rect.width);

  const cssY =
    (event.clientY - rect.top) *
    (view.height / rect.height);

  return cssToBoard(cssX, cssY, view);
}
```

`rect.width`와 `rect.height`가 0인 경우는 계산하지 않도록 방어해야 합니다.

중요한 점은 `devicePixelRatio`를 포인터 좌표에 직접 곱하지 않는다는 것입니다. 포인터 이벤트와 `getBoundingClientRect()`는 이미 CSS 픽셀 기준이며, DPR은 Canvas 백킹 버퍼를 선명하게 만드는 단계에서 처리합니다.

## 화면 스크롤과 보드 이동은 다릅니다

두 종류의 이동을 구분해야 합니다.

### 페이지 스크롤

Canvas DOM 요소 자체가 브라우저 viewport 안에서 이동합니다.

```ts
canvas.getBoundingClientRect()
```

가 현재 위치를 알려주므로 `clientX - rect.left` 계산으로 반영됩니다.

### 보드 패닝

Canvas 자체는 그대로 있고, 보드 원점이 Canvas 안에서 이동합니다.

```text
view.offsetX
view.offsetY
```

가 담당합니다.

따라서 포인터 좌표 변환은 다음 순서가 됩니다.

```text
브라우저 client 좌표
→ Canvas 내부 CSS 좌표
→ offset 제거
→ zoom 제거
→ 보드 좌표
```

## 서버는 브라우저 좌표를 신뢰하지 않습니다

클라이언트에서 올바르게 계산했다고 해도 네트워크로 받은 좌표는 신뢰할 수 없는 입력입니다.

예를 들어 서버는 최소한 다음을 검사할 수 있습니다.

```text
x, y가 숫자인가?
유한한 값인가?
NaN이나 Infinity가 아닌가?
허용한 보드 범위 안인가?
현재 사용자가 해당 항목을 수정할 권한이 있는가?
항목의 baseVersion이 최신인가?
```

예:

```ts
const PositionSchema = z.object({
  x: z.number().finite().min(-100_000).max(100_000),
  y: z.number().finite().min(-100_000).max(100_000)
});
```

실제 범위는 서비스의 보드 크기와 데이터 모델에 맞춰 정합니다.

브라우저에서 적중 판정을 했다는 사실도 서버의 권한 검사를 대신하지 않습니다.

## React와 Canvas 연결

React는 상태를 선언적으로 관리하지만 Canvas API는 `ctx.fillRect()`, `ctx.stroke()`처럼 명령을 직접 호출하는 방식입니다.

`ref`와 Effect를 경계로 사용하면 둘의 역할을 분리할 수 있습니다.

```tsx
function BoardCanvas({ state }: { state: BoardViewState }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useLayoutEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;

    const ctx = resizeCanvas(
      canvas,
      state.viewport.width,
      state.viewport.height
    );

    renderBoard(ctx, state);
  }, [state]);

  return (
    <canvas
      ref={ref}
      aria-label="협업 보드"
    />
  );
}
```

흐름은 다음과 같습니다.

```text
React state 변경
→ 컴포넌트 갱신
→ Effect 실행
→ Canvas 컨텍스트 확보
→ 현재 state 전체를 그림
```

처음에는 이처럼 **상태가 바뀔 때 전체 다시 그리기**로 구현하는 편이 좋습니다. 구조가 단순하므로 상태와 화면이 어긋나는 문제를 찾기 쉽습니다.

### `useLayoutEffect`와 `useEffect`

Canvas 그리기를 DOM 갱신 직후, 브라우저가 화면을 그리기 전에 완료해야 깜빡임을 줄일 수 있다면 `useLayoutEffect`가 적합할 수 있습니다.

화면 표시 전에 반드시 끝날 필요가 없는 작업이라면 `useEffect`도 사용할 수 있습니다.

어느 쪽을 사용하든 핵심은 Canvas 객체를 React 상태 자체로 만들기보다 `ref`를 통해 명령형 API에 접근하고, Effect의 수명 안에서 필요한 자원을 정리하는 것입니다.

## Canvas 크기와 컨테이너 크기

고정 크기가 아니라 부모 영역에 맞춰 Canvas가 바뀐다면 DOM의 실제 크기 변화를 관찰해야 합니다.

예를 들어 `ResizeObserver`를 사용해 컨테이너의 CSS 크기를 React 상태나 viewport에 반영할 수 있습니다.

```ts
useEffect(() => {
  const element = containerRef.current;
  if (!element) return;

  const observer = new ResizeObserver(entries => {
    const entry = entries[0];
    if (!entry) return;

    const { width, height } = entry.contentRect;

    setViewport(view => ({
      ...view,
      width,
      height
    }));
  });

  observer.observe(element);

  return () => {
    observer.disconnect();
  };
}, []);
```

리스너나 observer는 컴포넌트가 사라질 때 정리합니다.

## 드래그와 Pointer Events

마우스, 펜, 터치를 하나의 입력 모델로 다루려면 Pointer Events를 사용할 수 있습니다.

드래그 시작 시 포인터를 capture하면 포인터가 Canvas 밖으로 잠시 벗어나도 같은 요소가 이후 이벤트를 계속 받을 수 있습니다.

```ts
function onPointerDown(event: React.PointerEvent<HTMLCanvasElement>) {
  event.currentTarget.setPointerCapture(event.pointerId);
  // 선택과 드래그 시작
}
```

드래그가 끝나면 필요에 따라 capture를 해제합니다.

```ts
function onPointerUp(event: React.PointerEvent<HTMLCanvasElement>) {
  if (event.currentTarget.hasPointerCapture(event.pointerId)) {
    event.currentTarget.releasePointerCapture(event.pointerId);
  }

  // 최종 좌표 저장 요청
}
```

포인터가 사라지거나 취소될 수 있으므로 `pointercancel`도 드래그 종료 경로로 다루는 편이 안전합니다.

```text
pointerdown
→ drag 시작

pointermove
→ 임시 위치 갱신

pointerup
→ 최종 위치 확정

pointercancel
→ 임시 drag 상태 정리
```

터치 환경에서 보드 드래그가 브라우저의 페이지 스크롤이나 확대 제스처와 충돌한다면 해당 상호작용 영역에 적절한 `touch-action` 정책이 필요할 수 있습니다.

예를 들어 전체 Canvas에서 브라우저 기본 터치 제스처를 막는 것이 실제 UI 요구에 맞는 경우에만:

```css
.board-canvas {
  touch-action: none;
}
```

를 사용할 수 있습니다. 페이지 스크롤이 필요한 화면이라면 무조건 `none`으로 두지 않습니다.

## 적중 판정

Canvas는 DOM 요소처럼 각 도형에 자동으로 클릭 이벤트를 연결해 주지 않습니다. 포인터 좌표를 보드 좌표로 변환한 뒤 어떤 항목 안에 들어왔는지 직접 판단해야 합니다.

기본 흐름은 다음과 같습니다.

```text
포인터의 화면 좌표
→ 보드 좌표로 변환
→ 후보 항목 찾기
→ 도형별 포함 여부 검사
→ 겹친 항목 중 가장 위의 항목 선택
```

예를 들어 축에 평행한 사각형이라면:

```ts
function containsPoint(
  item: RectItem,
  x: number,
  y: number
): boolean {
  return (
    x >= item.x &&
    x <= item.x + item.width &&
    y >= item.y &&
    y <= item.y + item.height
  );
}
```

### 겹친 항목의 순서

렌더링 순서가 다음이라면:

```ts
for (const item of items) {
  drawItem(ctx, item);
}
```

뒤에 그린 항목이 앞에 보입니다.

따라서 `items` 배열 자체가 z-order를 나타낸다면 적중 판정에서는 뒤에서부터 검사할 수 있습니다.

```ts
for (let i = items.length - 1; i >= 0; i--) {
  if (containsPoint(items[i], x, y)) {
    return items[i];
  }
}
```

이렇게 해야 사용자가 실제로 화면에서 가장 위에 보는 항목이 선택됩니다.

원, 회전 사각형, 경로처럼 도형이 복잡하면 해당 도형의 기하학에 맞는 포함 판정이 필요합니다.

## 공간 인덱스는 필요할 때 도입합니다

항목 수가 적으면 매 포인터 이벤트마다 전체 배열을 검사해도 충분할 수 있습니다.

```text
항목 100개
→ 뒤에서부터 순회
→ 첫 적중 항목 반환
```

항목이 수만 개로 증가하고 실제 프로파일링에서 적중 판정이 병목이라는 사실이 확인되면 다음 구조를 검토할 수 있습니다.

- grid
- quadtree
- R-tree
- bounding box 기반 후보 인덱스

공간 인덱스의 목적은 정확한 도형 판정을 없애는 것이 아니라 **검사할 후보 수를 먼저 줄이는 것**입니다.

```text
공간 인덱스
→ 후보 10개 선택
→ 실제 도형 포함 판정
→ 최종 적중 항목 선택
```

## 애니메이션

연속 애니메이션이 필요하다면 `requestAnimationFrame()`을 사용할 수 있습니다.

```ts
let frame = 0;

function tick(time: number) {
  renderInterpolated(time);
  frame = requestAnimationFrame(tick);
}

frame = requestAnimationFrame(tick);
```

`requestAnimationFrame()`의 콜백은 브라우저가 다음 화면 갱신을 준비할 때 호출됩니다.

화면이나 컴포넌트가 사라질 때 예약된 프레임을 취소합니다.

```ts
cancelAnimationFrame(frame);
```

React에서는 Effect 안에서 시작했다면 같은 Effect의 cleanup에서 종료하는 구조가 명확합니다.

```tsx
useEffect(() => {
  let frame = 0;
  let stopped = false;

  function tick(time: number) {
    if (stopped) return;

    renderInterpolated(time);
    frame = requestAnimationFrame(tick);
  }

  frame = requestAnimationFrame(tick);

  return () => {
    stopped = true;
    cancelAnimationFrame(frame);
  };
}, []);
```

여러 Effect가 같은 Canvas에 각각 독립적인 animation loop를 시작하지 않도록 렌더링 책임을 한 곳에 모읍니다.

## 프레임 수를 시간으로 사용하지 않습니다

백그라운드 탭이나 절전 상태에서는 `requestAnimationFrame()` 호출 빈도가 크게 낮아질 수 있습니다.

따라서 다음처럼 생각하면 안 됩니다.

```text
60 frame = 정확히 1초
```

애니메이션 진행률은 콜백에 전달되는 시간이나 다른 monotonic time 기준으로 계산합니다.

```ts
function tick(time: number) {
  const elapsed = time - startedAt;
  renderAt(elapsed);
}
```

서버 타임아웃, 게임 규칙의 확정 시간, 데이터 만료 같은 서버 권한이 필요한 시간은 클라이언트 프레임 수를 기준으로 결정하지 않습니다.

## 원격 상태 보간

원격 커서나 다른 사용자의 드래그 좌표는 네트워크를 통해 일정하지 않은 간격으로 도착할 수 있습니다.

받은 좌표 사이를 화면에서 부드럽게 보간할 수 있지만, 보간된 값은 **표시용 값**입니다.

```text
서버 또는 네트워크에서 받은 좌표
→ 화면 표시용 보간
→ Canvas 렌더링
```

보간한 좌표를 다시 서버의 확정 상태로 간주하지 않습니다.

최종 확정 좌표가 도착하면 임시 보간 상태보다 서버 확정 값을 우선합니다.

## 텍스트 입력

Canvas 안에 자체 텍스트 편집기를 구현하려면 단순히 글자를 그리는 것 이상의 기능이 필요합니다.

예:

- IME 조합 입력
- caret
- 선택 영역
- 복사·붙여넣기
- 실행 취소
- 모바일 가상 키보드
- 키보드 이동
- 스크린 리더
- 입력기별 조합 이벤트

따라서 일반적인 보드 애플리케이션에서는 Canvas 위에 실제 HTML `input`이나 `textarea`를 겹쳐 사용하는 편이 적합합니다.

```text
Canvas
→ 배경
→ 도형
→ 연결선
→ 선택 윤곽
→ 원격 커서

DOM
→ 폼
→ 메뉴
→ 대화 상자
→ 텍스트 입력
→ 상태 안내
→ 키보드용 보조 UI
```

### DOM 입력 위치 맞추기

보드 좌표에 있는 항목 위에 `textarea`를 겹쳐 놓으려면 같은 `boardToCss()` 변환을 사용합니다.

```ts
const position = boardToCss(
  item.x,
  item.y,
  viewport
);
```

이렇게 하면 Canvas 렌더링과 DOM 오버레이가 같은 좌표 규칙을 공유합니다.

## 접근성

Canvas에 그려진 픽셀만으로는 스크린 리더가 각 항목의 의미, 순서와 상태를 충분히 파악하기 어렵습니다.

`aria-label` 하나를 Canvas에 추가하는 것만으로 모든 항목이 접근 가능해지는 것은 아닙니다.

다음과 같은 별도 DOM 경로를 제공합니다.

- Canvas 전체의 목적을 설명하는 접근 가능한 이름
- 보드 항목을 탐색할 수 있는 DOM 목록
- 현재 선택된 항목과 속성 표시
- 키보드로 항목을 선택·이동·삭제할 수 있는 동작
- 색상 외에도 구분 가능한 선택·오류·충돌 표시
- 저장 완료와 충돌 같은 상태 변화 안내
- 동작 줄이기 설정 반영

예를 들어 시각적 Canvas와 별도로 항목 목록을 둘 수 있습니다.

```tsx
<ul aria-label="보드 항목">
  {items.map(item => (
    <li key={item.id}>
      <button
        type="button"
        onClick={() => selectItem(item.id)}
      >
        {item.title}
      </button>
    </li>
  ))}
</ul>
```

Canvas와 DOM 목록은 같은 애플리케이션 상태를 읽어야 합니다.

```text
같은 BoardViewState
      ├─→ Canvas 시각 렌더링
      └─→ DOM 접근성 UI
```

둘이 서로 다른 상태 복사본을 따로 관리하면 선택 상태가 어긋날 수 있습니다.

## 키보드 조작

포인터만으로 가능한 기능을 만들면 키보드 사용자는 같은 작업을 수행할 수 없습니다.

예를 들어 선택된 항목을 화살표 키로 움직이는 경로를 제공할 수 있습니다.

```text
ArrowLeft  → x - step
ArrowRight → x + step
ArrowUp    → y - step
ArrowDown  → y + step
Delete     → 삭제 요청
Escape     → 선택 또는 임시 작업 취소
```

키 입력 역시 최종적으로는 포인터 입력과 같은 애플리케이션 명령을 호출하도록 하면 규칙이 중복되지 않습니다.

```text
pointer drag ─┐
              ├─→ moveItem command → 서버 검증
keyboard move ┘
```

## 상태 안내

저장이나 충돌이 비동기로 발생한다면 화면 색상만 바꾸지 말고 보조 기술에도 상태를 전달할 수 있어야 합니다.

예를 들어 일반적인 진행 상태는 `role="status"`로 알릴 수 있습니다.

```tsx
<div role="status" aria-live="polite">
  {saveMessage}
</div>
```

즉시 사용자의 주의가 필요한 오류는 상황에 따라 더 강한 알림을 사용할 수 있지만, 모든 사소한 변화에 `alert`를 사용하면 지나치게 방해가 될 수 있습니다.

## 동작 줄이기

사용자가 운영체제에서 동작 줄이기를 요청했다면 불필요한 애니메이션을 줄일 수 있습니다.

```ts
const reduceMotion = window.matchMedia(
  "(prefers-reduced-motion: reduce)"
).matches;
```

예를 들어 원격 커서 이동을 길게 보간하거나 선택 항목을 반복해서 흔드는 효과는 줄일 수 있습니다.

애플리케이션 상태 자체를 생략하는 것이 아니라 **장식적 움직임을 줄이는 것**이 목적입니다.

## 이미지와 Canvas 보안

Canvas에 외부 이미지를 그릴 때는 출처와 CORS 정책을 고려해야 합니다.

다른 출처의 이미지를 적절한 CORS 허용 없이 Canvas에 그리면 브라우저가 그 Canvas를 **origin-clean하지 않은 상태**, 흔히 "tainted canvas"라고 부르는 상태로 만들 수 있습니다.

그 뒤 다음 작업이 `SecurityError`로 실패할 수 있습니다.

- `getImageData()`
- `toDataURL()`
- `toBlob()`

픽셀 읽기나 Canvas 내보내기가 필요하다면 이미지 서버의 CORS 설정과 로딩 방식을 함께 설계해야 합니다.

예를 들어 CORS를 사용하는 이미지는 `src`를 지정하기 전에 `crossOrigin`을 설정해야 하는 경우가 있습니다.

```ts
const image = new Image();
image.crossOrigin = "anonymous";
image.src = url;
```

이 코드만으로 허용되는 것은 아니며, 이미지 서버가 적절한 CORS 응답 헤더를 보내야 합니다.

## 업로드 이미지 검증

사용자가 올린 이미지도 신뢰할 수 없는 입력입니다.

최소한 다음 정책을 검토합니다.

- 업로드 파일 최대 바이트 수
- 허용 MIME type
- 실제 디코딩 가능한 이미지인지
- 최대 가로·세로 크기
- 최대 총 픽셀 수
- 디코딩 실패 처리
- 저장·전송 시 콘텐츠 타입 일관성

압축 파일 크기가 작더라도 해상도가 매우 큰 이미지는 디코딩 뒤 많은 메모리를 사용할 수 있으므로 파일 바이트 수와 픽셀 수를 별도로 제한하는 편이 안전합니다.

SVG나 HTML처럼 마크업을 포함할 수 있는 콘텐츠를 사용자가 업로드했다면 검증하지 않은 문자열을 `innerHTML` 등으로 DOM에 삽입하지 않습니다. SVG를 허용해야 한다면 저장, 제공, DOM 삽입 여부에 맞는 별도 보안 정책을 마련합니다.

## 전체 다시 그리기부터 시작합니다

처음부터 부분 렌더링 시스템을 만들 필요는 없습니다.

기본 구현:

```text
상태 변경
→ Canvas 전체 clear
→ 현재 상태 전체 render
```

장점:

- 구현이 단순함
- 상태와 화면의 일관성을 유지하기 쉬움
- 버그 재현이 쉬움
- 렌더링 순서를 한 곳에서 볼 수 있음

실제 측정에서 전체 렌더링이 병목이라는 사실이 확인된 뒤 최적화합니다.

## 성능 확인

최적화 전에 무엇이 느린지 측정합니다.

확인할 값:

- 한 프레임 전체 렌더링 시간
- 항목 수 증가에 따른 `drawItem()` 시간
- 적중 판정 시간
- 포인터 이벤트 발생 빈도
- React 렌더링 시간
- Canvas 그리기 시간
- 백킹 버퍼 크기와 메모리
- 이미지 디코딩 비용
- 원격 커서와 드래그 메시지 빈도
- 한 프레임 안에서 발생하는 불필요한 반복 렌더링 횟수

브라우저의 Performance 도구에서 긴 프레임이 실제로 어디에서 발생하는지 확인합니다.

## 필요한 경우의 최적화

측정으로 병목이 확인되면 문제에 맞는 최적화를 선택합니다.

### 포인터 이벤트 합치기

`pointermove`가 매우 자주 발생한다면 모든 이벤트마다 즉시 전체 렌더링할 필요가 없을 수 있습니다.

```text
여러 pointermove
→ 최신 좌표만 상태에 반영
→ 다음 animation frame에서 한 번 렌더링
```

### 변경 영역만 다시 그리기

화면 전체가 매우 크고 일부만 변경된다면 dirty rectangle을 사용할 수 있습니다.

하지만 다음 요소가 있으면 계산이 복잡해집니다.

- 그림자
- 회전
- 겹침
- 연결선
- 반투명 합성
- 확대·축소

따라서 단순한 전체 다시 그리기보다 실제로 이득이 있는지 측정합니다.

### 오프스크린 Canvas

변하지 않는 배경이나 계산 비용이 큰 레이어를 별도 Canvas에 미리 그린 뒤 합성할 수 있습니다.

```text
정적 배경 layer
동적 item layer
cursor layer
```

하지만 레이어마다 추가 백킹 버퍼 메모리가 필요하므로 무조건 성능이 좋아지는 것은 아닙니다.

### 공간 인덱스

렌더링보다 적중 판정이 병목이라면 quadtree나 R-tree 같은 공간 인덱스를 검토합니다.

최적화는 병목의 종류와 맞아야 합니다.

```text
렌더링이 느림
→ 공간 인덱스만 추가
→ 반드시 해결되는 것은 아님

적중 판정이 느림
→ dirty rectangle만 추가
→ 반드시 해결되는 것은 아님
```

## 이벤트와 자원 정리

Canvas 자체보다 주변에 붙은 자원이 수명 문제를 만들기 쉽습니다.

예:

- `requestAnimationFrame`
- `setInterval`
- `setTimeout`
- `ResizeObserver`
- `window` 이벤트 리스너
- `document` 이벤트 리스너
- Pointer capture
- 이미지 로딩 callback

컴포넌트가 사라진 뒤에도 callback이 계속 실행되면 불필요한 렌더링, 메모리 보존 또는 이미 사라진 상태 접근이 발생할 수 있습니다.

Effect에서 등록했다면 cleanup에서 대응되는 해제를 두는 습관이 중요합니다.

```ts
useEffect(() => {
  function onKeyDown(event: KeyboardEvent) {
    // ...
  }

  window.addEventListener("keydown", onKeyDown);

  return () => {
    window.removeEventListener("keydown", onKeyDown);
  };
}, []);
```

## 흔한 실수

- Canvas 픽셀을 애플리케이션 데이터로 사용합니다.
- Canvas를 지운 뒤 상태만으로 화면을 복원할 수 없습니다.
- 보드 좌표, CSS 픽셀과 장치 픽셀을 같은 좌표로 취급합니다.
- 렌더링에서는 viewport 확대·이동을 적용하지만 포인터 역변환에는 같은 규칙을 적용하지 않습니다.
- `devicePixelRatio`를 포인터 좌표에 불필요하게 다시 곱합니다.
- CSS 표시 크기와 백킹 버퍼 크기를 항상 같은 값으로 둡니다.
- `canvas.width`나 `height` 변경이 내용과 컨텍스트 상태를 초기화한다는 점을 놓칩니다.
- 크기 변경 때 `scale()`을 계속 호출해 transform을 누적합니다.
- 반응형 CSS로 Canvas가 추가 확대되었는데 `getBoundingClientRect()` 크기를 고려하지 않습니다.
- `zoom=0` 같은 잘못된 viewport 값을 허용합니다.
- 브라우저가 계산한 보드 좌표를 서버에서 그대로 신뢰합니다.
- 적중 판정에서 겹친 항목의 z-order를 고려하지 않습니다.
- 드래그 중 포인터가 Canvas 밖으로 나가면 종료 상태를 잃습니다.
- `pointercancel`을 처리하지 않아 임시 드래그 상태가 남습니다.
- 여러 Effect가 각각 animation loop를 시작합니다.
- 애니메이션, observer와 전역 이벤트 리스너를 정리하지 않습니다.
- 백그라운드 탭에서도 프레임 수가 일정하다고 가정합니다.
- 모든 폼과 텍스트 입력을 Canvas 안에 직접 구현합니다.
- `aria-label` 하나만 있으면 Canvas 내부 항목 전체가 접근 가능하다고 가정합니다.
- 포인터 경로만 구현하고 키보드에서 같은 명령을 실행할 방법을 제공하지 않습니다.
- 외부 이미지를 그린 뒤 CORS와 Canvas origin-clean 상태를 고려하지 않습니다.
- 파일 바이트 수만 제한하고 매우 큰 이미지의 총 픽셀 수는 제한하지 않습니다.
- 측정하기 전에 부분 다시 그리기, 여러 레이어와 공간 인덱스를 모두 도입합니다.

## 완료 기준

- 보드 좌표, CSS 픽셀과 장치 픽셀의 역할을 구분합니다.
- `boardToCss()`와 `cssToBoard()`가 서로 대응되는 변환을 사용합니다.
- DPR은 백킹 버퍼 해상도에 적용하고 포인터 좌표에는 불필요하게 중복 적용하지 않습니다.
- 저장된 상태만으로 Canvas 전체를 지우고 다시 그릴 수 있습니다.
- 렌더링 transform과 포인터 역변환에 동일한 viewport 정의를 사용합니다.
- Canvas 크기 변경 뒤 컨텍스트 transform과 필요한 스타일을 다시 설정합니다.
- React의 Effect와 `ref`를 통해 Canvas의 명령형 API를 관리합니다.
- 애니메이션, observer, 이벤트 리스너와 드래그 상태를 수명에 맞게 정리합니다.
- 적중 판정은 보드 좌표에서 수행하고 겹친 항목의 순서를 고려합니다.
- 브라우저에서 계산한 좌표를 서버가 다시 범위·권한·버전 기준으로 검사합니다.
- Canvas 밖에 텍스트 입력, 키보드 조작과 보조 기술이 사용할 DOM 경로를 제공합니다.
- 외부 이미지와 업로드 이미지의 CORS, 크기와 디코딩 위험을 고려합니다.
- 실제 성능 측정 결과에 따라 필요한 최적화만 적용합니다.

## 연결 exercise

현재 competency suite에는 Canvas 전용 exercise가 없습니다. 실제 프로젝트의 게임 화면을 구현할 때 이 문서를 JIT로 사용하고, 상태 관리와 실시간 전송은 [`realtime-board`](../../exercises/realtime-board/README.md)로 다시 확인합니다.
