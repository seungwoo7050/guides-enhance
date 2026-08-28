// [Implementation 3] Search data and required DOM references
const documents = [
  { id: "runtime", title: "JavaScript 실행 환경", body: "호출 스택, 태스크, 마이크로태스크와 취소" },
  { id: "browser", title: "브라우저 플랫폼", body: "DOM, CSS, 접근성과 방문 기록" },
  { id: "api", title: "HTTP API", body: "실행 중 입력 검증과 오류 응답" },
  { id: "realtime", title: "실시간 상태", body: "WebSocket 방, 스냅샷과 재연결" }
];

const form = document.querySelector("#search-form");
const input = document.querySelector("#query");
const results = document.querySelector("#results");
const status = document.querySelector("#status");

// [Implementation 4] Query parsing from the current URL
function parseLocation() {
  return new URL(location.href).searchParams.get("q")?.trim() ?? "";
}

// [Implementation 5] Text-only result rendering
function render(query) {
  input.value = query;
  const normalized = query.toLocaleLowerCase();
  const filtered = normalized
    ? documents.filter((doc) => `${doc.title} ${doc.body}`.toLocaleLowerCase().includes(normalized))
    : documents;

  results.replaceChildren(...filtered.map((doc) => {
    const article = document.createElement("article");
    article.className = "card";
    const heading = document.createElement("h3");
    heading.textContent = doc.title;
    const body = document.createElement("p");
    body.textContent = doc.body;
    article.append(heading, body);
    return article;
  }));
  status.textContent = `${filtered.length}개 결과`;
}

// [Implementation 6] Form submission and history entry
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = input.value.trim();
  const url = new URL(location.href);
  if (query) url.searchParams.set("q", query);
  else url.searchParams.delete("q");
  history.pushState(null, "", url);
  render(query);
});

// [Implementation 7] Back and forward restoration
window.addEventListener("popstate", () => render(parseLocation()));
render(parseLocation());
