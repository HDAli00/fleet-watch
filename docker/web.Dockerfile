FROM node:20-alpine AS deps
WORKDIR /build

# Trust host-provided CA bundle (for TLS-intercepting build environments).
COPY docker/ca-bundle.crt /usr/local/share/ca-certificates/host-ca-bundle.crt
RUN if [ -s /usr/local/share/ca-certificates/host-ca-bundle.crt ]; then \
      cat /usr/local/share/ca-certificates/host-ca-bundle.crt >> /etc/ssl/certs/ca-certificates.crt; \
    fi
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

COPY app/web/package.json app/web/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

FROM node:20-alpine AS build
WORKDIR /build
COPY --from=deps /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
COPY --from=deps /build/node_modules ./node_modules
COPY app/web/ ./
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD wget -qO- http://localhost/ >/dev/null || exit 1
