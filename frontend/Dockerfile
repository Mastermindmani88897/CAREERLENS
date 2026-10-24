# =============================================================================
# CareerLens — Production Frontend Dockerfile
# Multi-stage build with Node.js 20 build stage and Nginx Alpine runtime
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build static production bundle
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency specifications and install cleanly with frozen lockfile
COPY package.json package-lock.json ./
RUN npm ci

# Copy complete frontend source
COPY . .

# Build production SPA assets into /app/dist
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Minimal Nginx Runtime
# -----------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runner

# Remove default boilerplate web files
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled production bundle from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom reverse proxy and SPA configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose standard HTTP port
EXPOSE 80

# Health check to verify Nginx is actively serving index.html
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

# Launch Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
