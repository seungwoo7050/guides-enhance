import type { APIRoute } from "astro";
import { getPublishedResources } from "../lib/resources";

// [Implementation 9]
// Static endpoint output exposes summaries only and is regenerated with the same content build.
export const GET = (async () => {
  const resources = await getPublishedResources();
  return new Response(JSON.stringify(resources.map(({ summary }) => summary), null, 2), {
    headers: {
      "content-type": "application/json; charset=utf-8"
    }
  });
}) satisfies APIRoute;
