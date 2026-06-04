# Build stage
FROM node:20-slim AS builder

WORKDIR /app/frontend

COPY package*.json ./
RUN npm install

COPY . .

# Pass build-time variables (we use relative path for API so Nginx handles proxying)
ENV VITE_API_BASE_URL=""
RUN npm run build

# Serve stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]