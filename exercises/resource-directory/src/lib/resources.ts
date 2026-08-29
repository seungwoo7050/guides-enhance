import { getCollection, type CollectionEntry } from "astro:content";
import {
  countResourcesByCategory,
  selectRelatedResources,
  sortResourceRecords,
  toResourceSummary,
  type ResourceRecord,
  type ResourceSummary
} from "./resource-model";

export type ResourceEntry = CollectionEntry<"resources">;
export type PublishedResource = {
  entry: ResourceEntry;
  record: ResourceRecord;
  summary: ResourceSummary;
};

// [Implementation 3]
// Drafts are removed before sorting so every page and endpoint observes the same published set.
export async function getPublishedResources(): Promise<PublishedResource[]> {
  const entries = await getCollection("resources", ({ data }) => !data.draft);
  const byId = new Map(entries.map((entry) => [entry.id, entry]));
  const records = sortResourceRecords(entries.map(toRecord));

  return records.map((record) => {
    const entry = byId.get(record.id);
    if (!entry) throw new Error(`Resource entry disappeared during build: ${record.id}`);
    return { entry, record, summary: toResourceSummary(record) };
  });
}

export function getCategoryCounts(resources: readonly PublishedResource[]) {
  return countResourcesByCategory(resources.map(({ record }) => record));
}

export function getRelatedResources(
  resources: readonly PublishedResource[],
  current: PublishedResource,
  limit = 3
): PublishedResource[] {
  const selected = new Set(
    selectRelatedResources(
      resources.map(({ record }) => record),
      current.record,
      limit
    ).map(({ id }) => id)
  );
  return resources.filter(({ record }) => selected.has(record.id));
}

function toRecord(entry: ResourceEntry): ResourceRecord {
  return {
    id: entry.id,
    title: entry.data.title,
    summary: entry.data.summary,
    category: entry.data.category,
    tags: [...entry.data.tags],
    publishedAt: entry.data.publishedAt,
    ...(entry.data.updatedAt ? { updatedAt: entry.data.updatedAt } : {}),
    featured: entry.data.featured
  };
}
