import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer, request as proxyRequest } from "node:http";
import { extname, resolve, sep } from "node:path";

const host = "0.0.0.0";
const port = Number.parseInt(process.env.FRONTEND_PORT ?? "3000", 10);
const staticRoot = resolve(process.env.FRONTEND_DIST ?? "./dist");
const apiTarget = new URL(process.env.FRONTEND_API_PROXY_TARGET ?? "http://app:8000");

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function proxyApi(clientRequest, clientResponse) {
  const targetUrl = new URL(clientRequest.url ?? "/", apiTarget);
  const clientAddress = clientRequest.socket.remoteAddress ?? "";
  const forwardedFor = clientRequest.headers["x-forwarded-for"];
  const headers = {
    ...clientRequest.headers,
    host: apiTarget.host,
    "x-forwarded-for": forwardedFor ? `${forwardedFor}, ${clientAddress}` : clientAddress,
    "x-forwarded-host": clientRequest.headers.host ?? "",
    "x-forwarded-proto": clientRequest.headers["x-forwarded-proto"] ?? "http",
    "x-real-ip": clientAddress,
  };

  const upstreamRequest = proxyRequest(
    targetUrl,
    {
      method: clientRequest.method,
      headers,
    },
    (upstreamResponse) => {
      clientResponse.writeHead(upstreamResponse.statusCode ?? 502, upstreamResponse.headers);
      upstreamResponse.pipe(clientResponse);
    },
  );

  upstreamRequest.on("error", () => {
    if (!clientResponse.headersSent) {
      clientResponse.writeHead(502, { "content-type": "application/json; charset=utf-8" });
    }
    clientResponse.end(JSON.stringify({ detail: "Backend API is unavailable." }));
  });

  clientRequest.pipe(upstreamRequest);
}

async function existingFile(pathname) {
  let decodedPath;
  try {
    decodedPath = decodeURIComponent(pathname);
  } catch {
    return null;
  }

  const requestedPath = resolve(staticRoot, `.${decodedPath}`);
  if (requestedPath !== staticRoot && !requestedPath.startsWith(`${staticRoot}${sep}`)) {
    return null;
  }

  try {
    const fileStat = await stat(requestedPath);
    if (fileStat.isFile()) return requestedPath;
    if (fileStat.isDirectory()) {
      const indexPath = resolve(requestedPath, "index.html");
      if ((await stat(indexPath)).isFile()) return indexPath;
    }
  } catch {
    return null;
  }
  return null;
}

function sendFile(request, response, filePath) {
  const extension = extname(filePath).toLowerCase();
  const cacheControl = request.url?.startsWith("/assets/")
    ? "public, max-age=31536000, immutable"
    : "no-cache";
  response.writeHead(200, {
    "cache-control": cacheControl,
    "content-type": contentTypes[extension] ?? "application/octet-stream",
    "x-content-type-options": "nosniff",
  });
  if (request.method === "HEAD") {
    response.end();
    return;
  }
  const stream = createReadStream(filePath);
  stream.on("error", () => {
    if (!response.headersSent) response.writeHead(500);
    response.end();
  });
  stream.pipe(response);
}

const server = createServer(async (request, response) => {
  const requestUrl = new URL(request.url ?? "/", `http://${request.headers.host ?? "localhost"}`);
  if (requestUrl.pathname === "/api" || requestUrl.pathname.startsWith("/api/")) {
    proxyApi(request, response);
    return;
  }

  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405, { allow: "GET, HEAD" });
    response.end();
    return;
  }

  const requestedFile = await existingFile(requestUrl.pathname);
  const filePath = requestedFile ?? resolve(staticRoot, "index.html");
  try {
    await stat(filePath);
    sendFile(request, response, filePath);
  } catch {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Frontend build is unavailable.");
  }
});

server.listen(port, host, () => {
  console.log(`Frontend static server listening on http://${host}:${port}`);
});

function shutdown(signal) {
  console.log(`Received ${signal}, stopping frontend server.`);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 25_000).unref();
}

process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
