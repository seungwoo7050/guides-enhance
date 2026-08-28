import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./style.css";

// [Implementation 1] Root document metadata
export const metadata: Metadata = {
  title: "사용자 디렉터리",
  description: "요청 취소와 동적 프로필 경로를 포함한 사용자 검색"
};

export default function Layout({ children }: { children: ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}
