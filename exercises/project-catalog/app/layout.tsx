import type { Metadata } from "next";
import "./styles.css";

// [Implementation 5]
// 문서 언어와 메타데이터를 지정하고 전역 스타일시트를 불러옵니다.
export const metadata: Metadata = {
  title: "Project Catalog",
  description: "Searchable project catalog with version-aware editing"
};

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
