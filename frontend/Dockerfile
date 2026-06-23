FROM node:22-bookworm-slim AS build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production \
    FRONTEND_PORT=3000 \
    FRONTEND_DIST=/app/frontend/dist

WORKDIR /app/frontend

COPY --from=build /app/frontend/dist ./dist
COPY frontend/server.mjs ./server.mjs

EXPOSE 3000

STOPSIGNAL SIGTERM

CMD ["node", "server.mjs"]
