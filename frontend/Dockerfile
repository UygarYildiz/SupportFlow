# Production image of the dashboard for self-hosted installations (ADR-017): the static
# build served by nginx, which also proxies the API so the browser talks to one origin.
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Same-origin API (nginx proxies /api), and no demo login buttons.
ENV VITE_API_BASE_URL="" VITE_DEMO_MODE="false"
RUN npm run build

FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
