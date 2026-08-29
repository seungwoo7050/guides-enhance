export const RESOURCE_CATEGORIES = ["web", "data", "tooling"] as const;

export type ResourceCategory = (typeof RESOURCE_CATEGORIES)[number];

export const CATEGORY_LABELS: Record<ResourceCategory, string> = {
  web: "웹",
  data: "데이터",
  tooling: "도구"
};

export type ResourceRecord = {
  id: string;
  title: string;
  summary: string;
  category: ResourceCategory;
  tags: string[];
  publishedAt: Date;
  updatedAt?: Date;
  featured: boolean;
};

export type ResourceSummary = {
  id: string;
  title: string;
  summary: string;
  category: ResourceCategory;
  categoryLabel: string;
  tags: string[];
  publishedAt: string;
  updatedAt?: string;
  featured: boolean;
};

// [Implementation 2]
// Category identifiers are kept separate from labels so URLs stay stable when copy changes.
export function isResourceCategory(value: string): value is ResourceCategory {
  return RESOURCE_CATEGORIES.includes(value as ResourceCategory);
}

// [Implementation 2-1]
// Featured entries come first; equal entries use the latest meaningful date and then title.
export function sortResourceRecords(records: readonly ResourceRecord[]): ResourceRecord[] {
  return [...records].sort((left, right) => {
    if (left.featured !== right.featured) return left.featured ? -1 : 1;
    const byDate = effectiveDate(right).getTime() - effectiveDate(left).getTime();
    return byDate || left.title.localeCompare(right.title, "ko");
  });
}

// [Implementation 2-2]
// Dates are serialized before crossing from Astro build code into pages and endpoints.
export function toResourceSummary(resource: ResourceRecord): ResourceSummary {
  return {
    id: resource.id,
    title: resource.title,
    summary: resource.summary,
    category: resource.category,
    categoryLabel: CATEGORY_LABELS[resource.category],
    tags: [...resource.tags],
    publishedAt: resource.publishedAt.toISOString(),
    ...(resource.updatedAt ? { updatedAt: resource.updatedAt.toISOString() } : {}),
    featured: resource.featured
  };
}

// [Implementation 2-3]
// Count and related-item selection reuse the same normalized records used for route generation.
export function countResourcesByCategory(
  records: readonly ResourceRecord[]
): Record<ResourceCategory, number> {
  const counts: Record<ResourceCategory, number> = { web: 0, data: 0, tooling: 0 };
  for (const resource of records) counts[resource.category] += 1;
  return counts;
}

export function selectRelatedResources(
  records: readonly ResourceRecord[],
  current: ResourceRecord,
  limit = 3
): ResourceRecord[] {
  return sortResourceRecords(
    records.filter((resource) => resource.id !== current.id && resource.category === current.category)
  ).slice(0, limit);
}

function effectiveDate(resource: ResourceRecord): Date {
  return resource.updatedAt ?? resource.publishedAt;
}
