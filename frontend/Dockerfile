# frontend/Dockerfile

# 1. Build stage
FROM node:22-alpine AS builder

WORKDIR /app
COPY . .

RUN npm install
RUN npx next build

# 2. Runtime stage (minimal, fast)
FROM node:22-alpine AS runner

WORKDIR /app
COPY --from=builder /app/.next .next
COPY --from=builder /app/public public
COPY --from=builder /app/package.json .
COPY --from=builder /app/node_modules node_modules

ENV PORT=3000
EXPOSE 3000

CMD ["npm", "run", "start"]
