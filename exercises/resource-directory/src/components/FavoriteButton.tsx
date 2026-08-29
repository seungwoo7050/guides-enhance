import { useEffect, useState } from "react";

const STORAGE_KEY = "resource-directory:favorites";

// [Implementation 8]
// Browser storage is read only after hydration; malformed or unwritable values stay local to this widget.
export function FavoriteButton({
  resourceId,
  resourceTitle
}: {
  resourceId: string;
  resourceTitle: string;
}) {
  const [ready, setReady] = useState(false);
  const [favorite, setFavorite] = useState(false);
  const [message, setMessage] = useState("");
  const statusId = `favorite-status-${resourceId}`;

  useEffect(() => {
    setFavorite(readFavorites().has(resourceId));
    setReady(true);
  }, [resourceId]);

  function toggleFavorite() {
    const favorites = readFavorites();
    if (favorites.has(resourceId)) favorites.delete(resourceId);
    else favorites.add(resourceId);

    if (!writeFavorites(favorites)) {
      setMessage("브라우저 저장소에 즐겨찾기를 저장하지 못했습니다.");
      return;
    }

    setFavorite(favorites.has(resourceId));
    setMessage(
      favorites.has(resourceId) ? "즐겨찾기에 추가했습니다." : "즐겨찾기에서 제거했습니다."
    );
  }

  return (
    <>
      <button
        className="favorite-button"
        type="button"
        aria-pressed={favorite}
        aria-label={`${resourceTitle} 즐겨찾기 ${favorite ? "해제" : "추가"}`}
        aria-describedby={message ? statusId : undefined}
        disabled={!ready}
        onClick={toggleFavorite}
      >
        {ready ? (favorite ? "즐겨찾기 해제" : "즐겨찾기 추가") : "즐겨찾기 불러오는 중"}
      </button>
      <span id={statusId} className="visually-hidden" role="status">
        {message}
      </span>
    </>
  );
}

function readFavorites(): Set<string> {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    if (!Array.isArray(parsed)) return new Set();
    return new Set(
      parsed
        .filter((value): value is string => typeof value === "string")
        .slice(0, 200)
    );
  } catch {
    return new Set();
  }
}

function writeFavorites(favorites: Set<string>): boolean {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...favorites].sort()));
    return true;
  } catch {
    return false;
  }
}
