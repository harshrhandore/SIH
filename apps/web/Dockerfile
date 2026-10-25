FROM node:22-alpine AS build
WORKDIR /workspace
COPY package*.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/api-client/package.json packages/api-client/package.json
RUN npm ci
COPY apps/web apps/web
COPY packages/api-client packages/api-client
RUN npm run build --workspace apps/web
FROM node:22-alpine AS runtime
WORKDIR /workspace
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup -S -g 10001 ledger && adduser -S -u 10001 -G ledger ledger
COPY --from=build --chown=ledger:ledger /workspace/apps/web/.next/standalone ./
COPY --from=build --chown=ledger:ledger /workspace/apps/web/.next/static ./apps/web/.next/static
COPY --from=build --chown=ledger:ledger /workspace/apps/web/public ./apps/web/public
USER ledger
EXPOSE 3000
CMD ["node","apps/web/server.js"]
