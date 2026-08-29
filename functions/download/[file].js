// Serves /download/<file>.mp3 by fetching the file from R2 and returning it
// with Content-Disposition: attachment, so mobile browsers start a native
// download on a single tap instead of opening the player.

const MEDIA_BASE = "https://pub-da751ee904b24db7820f2d5b3d23eeb9.r2.dev";

export async function onRequestGet({ request, params }) {
  const file = params.file;
  if (typeof file !== "string" || !/^[A-Za-z0-9._-]+\.mp3$/.test(file)) {
    return new Response("Not found", { status: 404 });
  }

  const range = request.headers.get("range");
  const upstream = await fetch(`${MEDIA_BASE}/${file}`, {
    headers: range ? { Range: range } : {},
  });
  if (upstream.status !== 200 && upstream.status !== 206) {
    return new Response("Not found", { status: 404 });
  }

  const headers = new Headers();
  for (const k of ["content-length", "content-range", "accept-ranges", "etag", "last-modified"]) {
    const v = upstream.headers.get(k);
    if (v) headers.set(k, v);
  }
  headers.set("Content-Type", "audio/mpeg");
  headers.set("Content-Disposition", `attachment; filename="${file}"`);
  headers.set("Cache-Control", "public, max-age=3600");

  return new Response(upstream.body, { status: upstream.status, headers });
}
