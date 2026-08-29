export const SITE_NAME = "Resource Directory";
export const SITE_DESCRIPTION =
  "웹, 데이터, 개발 도구에 관한 작고 검증 가능한 참고 자료를 모은 정적 디렉터리입니다.";

// [Implementation 4]
// Canonical URLs must use the site configured by Astro; a missing origin stops the build.
export function buildPageTitle(title?: string): string {
  return title ? `${title} | ${SITE_NAME}` : SITE_NAME;
}

export function buildCanonicalUrl(pathname: string, site: URL | undefined): URL {
  if (!site) throw new Error("astro.config.mjs에 site를 설정해야 합니다.");
  const normalized = pathname.startsWith("/") ? pathname : `/${pathname}`;
  return new URL(normalized, site);
}
