# One image definition, three stages:
#   dev     - used by docker-compose.yml on your laptop (runs `next dev`)
#   build   - compiles the production app
#   prod    - a small image with only the compiled app, used in production
FROM node:24-alpine AS deps
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
# Install packages before copying the code, so Docker reuses this layer when
# only the code changes.
COPY package.json package-lock.json ./
RUN npm ci


FROM deps AS dev
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]


FROM deps AS build
COPY . .
# next.config.ts reads API_URL while building (its /api rewrite is fixed at
# build time), so it must be set here, not only when the container runs.
ARG API_URL=http://api:8000
ENV API_URL=$API_URL
RUN npm run build


FROM node:24-alpine AS prod
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
WORKDIR /app
# `output: "standalone"` puts a minimal server plus only the packages it needs
# in .next/standalone; static files and public/ are copied next to it.
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
