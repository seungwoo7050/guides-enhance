"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { searchUsers, type User } from "../lib/fake-api";

// [Implementation 3] Request-state union
type LoadState =
  | { status: "loading" }
  | { status: "success"; users: User[] }
  | { status: "error"; message: string };

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [name, setName] = useState("방문자");
  const [draftName, setDraftName] = useState("");
  const [state, setState] = useState<LoadState>({ status: "loading" });

  // [Implementation 4] Search cancellation on query change
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    searchUsers(query, controller.signal)
      .then((users) => setState({ status: "success", users }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "검색하지 못했습니다."
        });
      });
    return () => controller.abort();
  }, [query]);


  function commitDisplayName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = draftName.trim();
    if (!normalized) return;
    setName(normalized);
    setDraftName("");
  }

  // [Implementation 5] Loading, error, empty, and result rendering
  return <main>
    <h1>안녕하세요, {name}님</h1>
    <form onSubmit={commitDisplayName}>
      <label htmlFor="name">표시 이름</label>
      <input
        id="name"
        value={draftName}
        onChange={(event) => setDraftName(event.target.value)}
        maxLength={40}
      />
      <button type="submit">변경</button>
    </form>

    <section aria-labelledby="search-heading">
      <h2 id="search-heading">사용자 검색</h2>
      <label htmlFor="query">검색어</label>
      <input id="query" value={query} onChange={(event) => setQuery(event.target.value)} />
      {state.status === "loading" ? <p role="status">불러오는 중입니다.</p> : null}
      {state.status === "error" ? <p role="alert">{state.message}</p> : null}
      {state.status === "success" && state.users.length === 0 ? <p>검색 결과가 없습니다.</p> : null}
      {state.status === "success" ? <div className="grid">{state.users.map((user) =>
        <article className="card" key={user.id}>
          <h3>{user.displayName}</h3>
          <p>@{user.handle}</p>
          <Link href={`/profile/${user.handle}`}>프로필</Link>
        </article>
      )}</div> : null}
    </section>
  </main>;
}
