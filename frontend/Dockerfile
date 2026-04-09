# ══════════════════════════════════════════════
# Stage 1 — deps: install node_modules
# ══════════════════════════════════════════════
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ══════════════════════════════════════════════
# Stage 2 — builder: compile Next.js
# ══════════════════════════════════════════════
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# ══════════════════════════════════════════════
# Stage 3 — runner: minimal production image
# ══════════════════════════════════════════════
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy standalone server + static assets
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
# public/ is empty in this project but copy it for completeness
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
