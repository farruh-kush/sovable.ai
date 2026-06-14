FROM node:18-alpine

WORKDIR /app

ENV NODE_ENV=production

# install deps and build
COPY package.json package-lock.json* ./
COPY . .

RUN npm ci --omit=dev || npm install --production
RUN npm run build

EXPOSE 3000

CMD ["npm","start"]
