# Multi-stage: build admin-ui + me-ui, then serve via nginx
# context: services/ (one level up so we can COPY admin-ui/ + me-ui/)

FROM node:20-alpine AS admin-build
WORKDIR /build
COPY admin-ui/package.json admin-ui/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY admin-ui/ ./
RUN npm run build

FROM node:20-alpine AS me-build
WORKDIR /build
COPY me-ui/package.json me-ui/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY me-ui/ ./
RUN npm run build

FROM nginx:alpine
COPY dashboard/html/ /usr/share/nginx/html/
COPY --from=admin-build /build/dist/ /usr/share/nginx/html/admin-ui/
COPY --from=me-build /build/dist/ /usr/share/nginx/html/me-ui/
COPY dashboard/nginx.conf /etc/nginx/conf.d/default.conf
