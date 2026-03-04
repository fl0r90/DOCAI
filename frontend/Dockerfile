# Folosim o imagine de Node modernă și ușoară
FROM node:20-alpine

WORKDIR /app

# Copiem doar fișierele de dependințe prima dată (optimizare cache)
COPY package*.json ./

# Instalăm tot ce trebuie
RUN npm install

# Copiem restul codului sursă
COPY . .

# Expunem portul de Next.js
EXPOSE 3000

# Pornim în mod dev
CMD ["npm", "run", "dev"]
