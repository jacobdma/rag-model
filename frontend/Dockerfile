# Prod frontend image — a real Next.js production build (next build + next
# start), not the dev server. bookworm-slim (glibc) avoids musl issues with
# tailwind's native oxide/lightningcss binaries.
FROM node:20-bookworm-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_* values are inlined into the client bundle at BUILD time, so the
# browser-reachable backend address must be known here. Override HOST_IP for
# LAN access (the server's IP); default localhost works for same-machine use.
ARG NEXT_PUBLIC_HOST_IP=localhost
ARG NEXT_PUBLIC_BACKEND_PORT=8000
ENV NEXT_PUBLIC_HOST_IP=$NEXT_PUBLIC_HOST_IP
ENV NEXT_PUBLIC_BACKEND_PORT=$NEXT_PUBLIC_BACKEND_PORT
ENV NODE_ENV=production

RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
