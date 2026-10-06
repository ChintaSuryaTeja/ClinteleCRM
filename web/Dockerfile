FROM node:24-alpine

ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

# Install packages before copying the code, so Docker reuses this layer when
# only the code changes.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
