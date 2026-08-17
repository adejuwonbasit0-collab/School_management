# EduCore Enterprise School Management Platform
## Complete Installation & Deployment Guide

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 vCPUs | 4+ vCPUs |
| RAM | 4 GB | 8 GB |
| Storage | 20 GB SSD | 50 GB SSD |
| Node.js | 18.x | 20.x LTS |
| PostgreSQL | 14 | 15+ |
| Redis | 6 | 7+ |

---

## Quick Start (Docker)

```bash
# 1. Clone / extract the project
cd educore

# 2. Copy environment files
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env

# 3. Edit environment variables (see Environment Configuration below)
nano apps/api/.env

# 4. Start all services
docker-compose up -d

# 5. Run database migrations
docker-compose exec api npx prisma migrate deploy

# 6. Seed demo data
docker-compose exec api npx ts-node prisma/seed.ts

# 7. Access the platform
# Frontend: http://localhost:3000
# API:      http://localhost:3001/api
# API Docs: http://localhost:3001/api/docs
```

---

## Environment Configuration

### Backend (`apps/api/.env`)

```env
# Database
DATABASE_URL="postgresql://postgres:password@localhost:5432/educore"

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# JWT
JWT_SECRET=your-super-secret-jwt-key-min-32-chars
JWT_REFRESH_SECRET=your-refresh-secret-min-32-chars
JWT_EXPIRY=15m
JWT_REFRESH_EXPIRY=7d

# App
NODE_ENV=production
PORT=3001
API_URL=https://api.yourschool.com
FRONTEND_URL=https://yourschool.com

# Email (choose one)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@yourschool.com
SMTP_PASS=your-app-password
SENDGRID_API_KEY=

# File Storage
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
AWS_S3_BUCKET=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=

# AI
OPENAI_API_KEY=sk-...

# Payment Gateways (configure from dashboard, env for fallback)
PAYSTACK_SECRET_KEY=
FLUTTERWAVE_SECRET_KEY=
STRIPE_SECRET_KEY=
MONNIFY_API_KEY=
MONNIFY_CONTRACT_CODE=

# MFA
MFA_ISSUER=EduCore
```

### Frontend (`apps/web/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:3001/api
NEXT_PUBLIC_APP_NAME=EduCore
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

---

## Manual Installation (Without Docker)

### 1. Install Dependencies

```bash
# Root dependencies
npm install

# Backend
cd apps/api && npm install

# Frontend  
cd apps/web && npm install
```

### 2. Database Setup

```bash
cd apps/api

# Generate Prisma client
npx prisma generate

# Run migrations
npx prisma migrate deploy

# Seed data
npx ts-node prisma/seed.ts
```

### 3. Build for Production

```bash
# Build backend
cd apps/api && npm run build

# Build frontend
cd apps/web && npm run build
```

### 4. Start Services

```bash
# Start API (production)
cd apps/api && npm run start:prod

# Start Frontend (production)
cd apps/web && npm start
```

---

## Default Login Credentials

After seeding, use these credentials:

| Role | Email | Password |
|------|-------|----------|
| Super Admin | admin@educore.com | Admin@123 |
| Principal | principal@educore.com | Admin@123 |
| Teacher | teacher@educore.com | Admin@123 |
| Parent | parent@educore.com | Admin@123 |
| Student | student@educore.com | Admin@123 |
| Bursar | bursar@educore.com | Admin@123 |

**⚠️ Change all passwords immediately after first login.**

---

## Production Deployment

### VPS / DigitalOcean / AWS EC2

```bash
# 1. Install dependencies on server
sudo apt update && sudo apt install -y nodejs npm postgresql redis-server nginx

# 2. Configure PostgreSQL
sudo -u postgres createdb educore
sudo -u postgres createuser educore_user

# 3. Clone and install project
git clone <repo> /var/www/educore
cd /var/www/educore && npm install

# 4. Configure environment
cp apps/api/.env.example apps/api/.env
# Edit .env with production values

# 5. Build and migrate
npm run build
npm run migrate:prod

# 6. Use PM2 for process management
npm install -g pm2
pm2 start apps/api/dist/main.js --name educore-api
pm2 start npm --name educore-web -- start
pm2 save && pm2 startup
```

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/educore
server {
    listen 80;
    server_name yourschool.com www.yourschool.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourschool.com www.yourschool.com;

    ssl_certificate /etc/letsencrypt/live/yourschool.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourschool.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
    }
}
```

### Vercel (Frontend Only)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy frontend
cd apps/web
vercel --prod

# Set environment variables in Vercel dashboard
# NEXT_PUBLIC_API_URL = https://your-api-domain.com/api
```

---

## Docker Compose Services

The `docker-compose.yml` includes:

| Service | Port | Description |
|---------|------|-------------|
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis cache & queues |
| `api` | 3001 | NestJS backend API |
| `web` | 3000 | Next.js frontend |
| `nginx` | 80/443 | Reverse proxy |

---

## Health Checks

```bash
# API health
curl http://localhost:3001/api/health

# Database connectivity
curl http://localhost:3001/api/health/db

# Full system status
curl http://localhost:3001/api/health/full
```

---

## Troubleshooting

**Database connection fails:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql
# Check connection string in .env
psql $DATABASE_URL
```

**Redis connection fails:**
```bash
sudo systemctl start redis
redis-cli ping  # Should return PONG
```

**Build fails:**
```bash
# Clear caches
rm -rf apps/api/dist apps/web/.next node_modules
npm install && npm run build
```

**Prisma migration fails:**
```bash
cd apps/api
npx prisma migrate status
npx prisma migrate resolve --applied "migration_name"
```

---

## Backup & Restore

```bash
# Database backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Database restore
psql $DATABASE_URL < backup_20240101.sql

# Files backup (Cloudinary/S3 managed externally)
```

---

## Support

- Documentation: `/docs` directory
- API Reference: `http://localhost:3001/api/docs` (Swagger)
- Logs: `pm2 logs educore-api`
