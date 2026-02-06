# Deployment Manager

Central hub for managing deployments of all four Mebbert.com web applications.

## Deployment Scripts

All deployment operations are run from this directory (`C:\claude_projects\deployment-manager\`).

### Full Deploy (sync files + install deps + restart + verify)
```bash
python deploy.py <app|all>          # Deploy with confirmation prompt
python deploy.py <app|all> --yes    # Skip confirmation
```

### Status Check (read-only health checks)
```bash
python status.py <app|all>
```
Checks: service status, port listening, process running, HTTP response, recent logs.

### Quick Restart
```bash
python restart.py <app|all>
```

### View Logs
```bash
python logs.py <app>                # Last 50 lines
python logs.py <app> -n 100         # Last 100 lines
python logs.py <app> -f             # Follow real-time (Ctrl+C to stop)
python logs.py <app> --since "1 hour ago"
```

**App names:** `taskschedule`, `sevenhabitslist`, `recipeshoppinglist`, `tifootball`, `all`

### How It Works
- Uses `tarfile` (Python stdlib) + `scp` + `ssh` for file sync (no rsync needed)
- Excludes: venv/, .git/, __pycache__/, *.db, *.db-journal, data dirs
- Config in `config.py`, SSH utilities in `ssh_utils.py`
- SSH key auto-detected from `*.pem` in this directory

---

## Overview

This directory manages deployment for four sibling projects:

| Project | Tech Stack | Port | Subdomain | Status |
|---------|-----------|------|-----------|--------|
| **taskschedule** | Flask + SQLite | 5000 | http://taskschedule.mebbert.com:5000 | ✅ Deployed |
| **sevenhabitslist** | FastAPI + SQLite | 3002 | https://sevenhabitslist.mebbert.com | ✅ Deployed |
| **recipeshoppinglist** | FastAPI + SQLite | 3003 | https://recipeshoppinglist.mebbert.com | ✅ Deployed |
| **tifootball** | React + Node/Express + SQLite | 3001 | https://tifootball.mebbert.com | ✅ Deployed |

## Shared Infrastructure

### AWS EC2 Instance
- **IP Address:** 100.50.222.238 (Elastic IP)
- **Instance ID:** i-05582111840d4a971
- **Instance Type:** t2.micro (Free tier eligible)
- **Region:** us-east-1 (Virginia)
- **OS:** Amazon Linux 2
- **User:** ec2-user

### SSH Access
```bash
ssh -i "taskschedule-key.pem" ec2-user@100.50.222.238
```

Key location: `C:\claude_projects\deployment-manager\taskschedule-key.pem`

### Nginx Configuration
All HTTPS subdomains are configured in: `/etc/nginx/conf.d/subdomains.conf`

### DNS (Route 53)
- **Hosted Zone:** mebbert.com (Z040520630S50ZVHYL1YA)
- **DNS Records:** A records pointing subdomains to 100.50.222.238

---

## Project Details

### 1. Task Schedule (Flask)

**Local Path:** `C:\claude_projects\taskschedule`
**Remote Path:** `/home/ec2-user/taskschedule/`
**Service:** systemd (`taskschedule.service`)

**Key Features:**
- Task scheduling and household maintenance management
- Session-based authentication
- SQLite database with automatic backups (rotates .bak1 through .bak5)

**Deployment:**
```bash
# SSH to server
ssh -i "taskschedule-key.pem" ec2-user@taskschedule.mebbert.com

# Update application
cd /home/ec2-user/taskschedule
git pull origin main
sudo systemctl restart taskschedule

# Check status
sudo systemctl status taskschedule
sudo journalctl -u taskschedule -f
```

**Documentation:**
- AWS_DEPLOYMENT.md - Complete deployment instructions
- AWS_INFRASTRUCTURE.md - Infrastructure details and subdomain setup guide
- SCHEMA.md - Database schema documentation

---

### 2. Seven Habits List (FastAPI)

**Local Path:** `C:\claude_projects\sevenhabitslist\sevenhabitslist`
**Remote Path:** `/home/ec2-user/sevenhabitslist/`
**Service:** systemd (`sevenhabitslist.service`)

**Key Features:**
- Task management based on "7 Habits of Highly Effective People"
- Organized by life roles and weekly schedules
- Automated deployment scripts

**Deployment Scripts:**
The project includes Python automation scripts for easy deployment:

```bash
# Full deployment (sync files + install deps + restart)
python deploy.py

# Quick restart
python restart.py

# Health check
python status.py

# View logs
python logs.py           # Last 50 lines
python logs.py -f        # Follow real-time
python logs.py -n 100    # Custom line count
python logs.py --since "1 hour ago"
```

**Manual Deployment:**
```bash
# SSH to server
ssh -i "taskschedule-key.pem" ec2-user@100.50.222.238

# Update and restart
cd /home/ec2-user/sevenhabitslist
# Files synced via deploy.py
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sevenhabitslist
```

**Documentation:**
- CLAUDE.md - Quick reference
- DEPLOYMENT_SCRIPTS.md - Detailed script documentation with examples

---

### 3. Recipe Shopping List (FastAPI)

**Local Path:** `C:\claude_projects\recipeshoppinglist`
**Remote Path:** `/home/ec2-user/recipeshoppinglist/`
**Service:** systemd (`recipeshoppinglist.service`)

**Key Features:**
- Family recipe management
- Shopping list generator from selected recipes
- Recipe discovery from 4 external sources (TheMealDB, BBC Good Food, Skinnytaste, Hey Grill Hey)
- Unit conversion and ingredient parsing

**Deployment:**
```bash
# SSH to server
ssh -i "taskschedule-key.pem" ec2-user@100.50.222.238

# Update application
cd /home/ec2-user/recipeshoppinglist
# Copy updated files via rsync/scp
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart recipeshoppinglist

# Check status
sudo systemctl status recipeshoppinglist
sudo journalctl -u recipeshoppinglist -f
```

**Environment:**
- PORT=3003 (default, can be overridden)
- Database auto-created at `data/recipes.db`

**Documentation:**
- CLAUDE.md (367 lines) - Comprehensive documentation including auth plans

---

### 4. TI Football (React + Node/Express)

**Local Path:** `C:\claude_projects\tifootball`
**Remote Path:** `/home/ec2-user/tifootball/`
**Service:** systemd (`tifootball.service`)

**Key Features:**
- Full-stack fantasy football simulation
- React frontend (Vite build)
- Express API backend
- NFL team and player data

**Build & Deploy Process:**
```bash
# Local: Build frontend
cd C:\claude_projects\tifootball\client
npm run build  # Outputs to dist/

# Deploy to server
# 1. Copy entire project to /home/ec2-user/tifootball/
# 2. SSH to server
ssh -i "taskschedule-key.pem" ec2-user@100.50.222.238

# 3. Install dependencies
cd /home/ec2-user/tifootball/server
npm install

# 4. Initialize database
npm run seed

# 5. Create systemd service (use taskschedule.service as template)
sudo nano /etc/systemd/system/tifootball.service

# 6. Enable and start
sudo systemctl enable --now tifootball

# 7. Check status
sudo systemctl status tifootball
```

**Development Scripts:**
```bash
# Client
npm run dev      # Dev server on port 3000
npm run build    # Production build
npm run preview  # Preview production build

# Server
npm run dev                    # Dev mode with auto-reload
npm start                      # Production server
npm run seed                   # Initialize database
npm run populate-schedule      # Import NFL schedule
npm run simulate               # Run game simulations
```

**Documentation:**
- CLAUDE.md - AWS subdomain info, deployment steps, season setup checklist
- README.md - Basic setup instructions

---

## Common Operations

### Check All Services Status
```bash
ssh -i "taskschedule-key.pem" ec2-user@100.50.222.238
sudo systemctl status taskschedule sevenhabitslist recipeshoppinglist tifootball
```

### View All Logs
```bash
# Real-time logs from all services
sudo journalctl -u taskschedule -u sevenhabitslist -u recipeshoppinglist -u tifootball -f

# Last 50 lines from each
sudo journalctl -u taskschedule -n 50
sudo journalctl -u sevenhabitslist -n 50
sudo journalctl -u recipeshoppinglist -n 50
sudo journalctl -u tifootball -n 50
```

### Restart All Services
```bash
ssh -i "taskschedule-key.pem" ec2-user@100.50.222.238
sudo systemctl restart taskschedule sevenhabitslist recipeshoppinglist tifootball
```

### Nginx Management
```bash
# Test nginx configuration
sudo nginx -t

# Reload nginx (after config changes)
sudo systemctl reload nginx

# Restart nginx
sudo systemctl restart nginx

# View nginx error logs
sudo tail -f /var/log/nginx/error.log
```

---

## Port Allocation

| Port | Application | Protocol |
|------|------------|----------|
| 22   | SSH | TCP |
| 80   | HTTP (Nginx) | TCP |
| 443  | HTTPS (Nginx) | TCP |
| 3001 | tifootball | HTTP (proxied by Nginx) |
| 3002 | sevenhabitslist | HTTP (proxied by Nginx) |
| 3003 | recipeshoppinglist | HTTP (proxied by Nginx) |
| 5000 | taskschedule | HTTP (direct access) |

**Security Group:** sg-08148e411586cd1fe (taskschedule-sg)

---

## Database Locations

All projects use SQLite (file-based databases):

| Project | Database Path |
|---------|--------------|
| taskschedule | `/home/ec2-user/taskschedule/database.db` |
| sevenhabitslist | `/home/ec2-user/sevenhabitslist/data/sevenhabits.db` |
| recipeshoppinglist | `/home/ec2-user/recipeshoppinglist/data/recipes.db` |
| tifootball | `/home/ec2-user/tifootball/server/db/tifootball.db` |

**Backup Strategy:**
- taskschedule: Automatic rotating backups (.bak1 through .bak5)
- Others: Manual backups recommended

---

## Systemd Service Template

Reference template for new services:

```ini
[Unit]
Description=<App Name> Application
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/<app-directory>
Environment="PATH=/home/ec2-user/<app-directory>/venv/bin"
ExecStart=/home/ec2-user/<app-directory>/venv/bin/<command>
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Examples:**

**FastAPI (sevenhabitslist/recipeshoppinglist):**
```ini
ExecStart=/home/ec2-user/sevenhabitslist/venv/bin/uvicorn main:app --host 0.0.0.0 --port 3002
```

**Node.js (tifootball):**
```ini
WorkingDirectory=/home/ec2-user/tifootball/server
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/node index.js
```

---

## Deployment Workflows

### Standard Python (FastAPI/Flask) Deployment

1. **Sync files** (exclude: venv/, data/, .git/, __pycache__)
2. **SSH to server**
3. **Activate virtual environment** or create if first deploy
4. **Install/update dependencies:** `pip install -r requirements.txt`
5. **Restart systemd service:** `sudo systemctl restart <service>`
6. **Verify:** `sudo systemctl status <service>`
7. **Check logs:** `sudo journalctl -u <service> -f`

### Node.js (tifootball) Deployment

1. **Build frontend locally:** `cd client && npm run build`
2. **Sync entire project** to server
3. **SSH to server**
4. **Install server dependencies:** `cd server && npm install`
5. **Restart service:** `sudo systemctl restart tifootball`
6. **Verify:** `sudo systemctl status tifootball`

---

## Security Considerations

### Current Security Status

⚠️ **Identified Issues:**
- taskschedule: Plain-text passwords, no HTTPS (port 5000 direct access)
- All apps: SSH access from anywhere (0.0.0.0/0)
- All apps: Broad security group rules

✅ **HTTPS Configured:**
- sevenhabitslist
- recipeshoppinglist
- tifootball

### Optional Nginx Authentication

For protecting apps with centralized authentication, see:
- `C:\claude_projects\recipeshoppinglist\CLAUDE.md` - Nginx auth_request module setup
- Centralized auth service on port 3010
- Session cookies shared across subdomains

### Recommended Improvements

1. **Add HTTPS to taskschedule** (Let's Encrypt/certbot)
2. **Implement password hashing** (bcrypt/argon2)
3. **Restrict SSH access** to specific IP ranges
4. **Implement rate limiting** on Nginx
5. **Add database backup automation**

---

## Troubleshooting

### Service Won't Start
```bash
# Check service status and recent logs
sudo systemctl status <service>
sudo journalctl -u <service> -n 100

# Check if port is in use
sudo netstat -tlnp | grep <port>

# Verify file permissions
ls -la /home/ec2-user/<app-directory>
```

### Application Not Accessible
```bash
# Check nginx is running
sudo systemctl status nginx

# Test nginx config
sudo nginx -t

# Check application is listening
curl http://localhost:<port>

# Check firewall/security group allows port
```

### Database Issues
```bash
# Check database file exists and is writable
ls -la /home/ec2-user/<app>/data/

# Check disk space
df -h

# Restore from backup (taskschedule example)
cd /home/ec2-user/taskschedule
cp database.db.bak1 database.db
sudo systemctl restart taskschedule
```

### Python Virtual Environment Issues
```bash
# Recreate virtual environment
cd /home/ec2-user/<app>
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Cost Information

**Current Monthly Costs (approximate):**
- EC2 t2.micro: Free tier (12 months), then ~$8.50/month
- Elastic IP: Free when associated
- Route 53 hosted zone: ~$0.50/month
- DNS queries: ~$0.40 per million queries
- Data transfer: First 100 GB/month free

**Total after free tier:** ~$9-10/month

---

## Quick Reference Commands

```bash
# SSH into server
ssh -i "taskschedule-key.pem" ec2-user@100.50.222.238

# Check all service statuses
sudo systemctl status taskschedule sevenhabitslist recipeshoppinglist tifootball

# Restart all services
sudo systemctl restart taskschedule sevenhabitslist recipeshoppinglist tifootball

# Follow all logs in real-time
sudo journalctl -u taskschedule -u sevenhabitslist -u recipeshoppinglist -u tifootball -f

# Check nginx status
sudo systemctl status nginx
sudo nginx -t

# Check disk space
df -h

# Check running processes
ps aux | grep -E '(python|node|uvicorn)'

# Check listening ports
sudo netstat -tlnp
```

---

## Related Documentation

- **AWS_DEPLOYMENT.md:** `/home/ec2-user/taskschedule/AWS_DEPLOYMENT.md` (on server)
- **AWS_INFRASTRUCTURE.md:** `C:\claude_projects\taskschedule\AWS_INFRASTRUCTURE.md`
- **Individual project CLAUDE.md files:** See each project directory for detailed docs

---

## Future Enhancements

- [ ] Create unified deployment script for all projects
- [ ] Set up automated database backups to S3
- [ ] Implement monitoring/alerting (CloudWatch)
- [ ] Add HTTPS to taskschedule
- [ ] Implement centralized authentication
- [ ] Create CI/CD pipeline (GitHub Actions)
- [ ] Add health check monitoring
- [ ] Implement log aggregation
