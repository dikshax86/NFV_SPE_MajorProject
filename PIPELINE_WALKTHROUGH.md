# NFV DevOps Project - Pipeline Walkthrough

This document walks you through every file in the project, what it does, and how the entire pipeline flows end-to-end.

---

## Project Structure

```
nfv-devops-project/
├── firewall-service/           # VNF 1: Firewall
│   ├── app.py                  # Flask API - inspects and blocks traffic
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Container blueprint
│   └── tests/
│       └── test_app.py         # Unit tests (7 test cases)
│
├── switch-service/             # VNF 2: Switch/Router
│   ├── app.py                  # Flask API - routes traffic to firewall
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       └── test_app.py         # Unit tests (5 test cases, uses mocking)
│
├── monitor-service/            # VNF 3: Monitor
│   ├── app.py                  # Flask API - logs traffic, sends to ELK
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       └── test_app.py         # Unit tests (4 test cases)
│
├── docker-compose.yml          # Runs ALL services + ELK stack together
├── Jenkinsfile                 # CI/CD pipeline definition
│
├── k8s/                        # Kubernetes manifests
│   ├── firewall-deployment.yaml
│   ├── switch-deployment.yaml
│   ├── monitor-deployment.yaml
│   └── firewall-hpa.yaml      # Horizontal Pod Autoscaler (advanced)
│
├── ansible/                    # Configuration management
│   ├── inventory/
│   │   └── hosts               # Target server list
│   ├── playbooks/
│   │   └── site.yml            # Main playbook
│   └── roles/
│       ├── docker/tasks/main.yml      # Installs Docker
│       ├── kubernetes/tasks/main.yml  # Installs K8s tools
│       └── deploy/tasks/main.yml      # Deploys the app
│
├── logstash/
│   └── pipeline/
│       └── logstash.conf       # Logstash pipeline config
│
├── WALKTHROUGH_GUIDE.md        # Detailed study guide for all tools
└── PIPELINE_WALKTHROUGH.md     # This file
```

---

## PHASE 1: Writing the Microservices

### What happens here:
You write 3 Flask applications that simulate Network Functions (Firewall, Switch, Monitor).

### File-by-file breakdown:

### `firewall-service/app.py`
- **Purpose**: Acts as a virtual firewall - inspects incoming requests and blocks malicious ones
- **Endpoint**: `POST /check` - receives a message and client IP
- **Logic**:
  1. Parses JSON body with `request.get_json(silent=True)`
  2. Reads client IP from `X-Forwarded-For` header
  3. Checks IP against `BLOCKED_IPS` list → returns 403 if blocked
  4. Checks message for `BLOCKED_KEYWORDS` → returns 403 if found
  5. Returns 200 with "allowed" status if clean
- **Health endpoint**: `GET /health` - used by Docker and K8s for health checks
- **Key learning**: How REST APIs work, HTTP status codes, header inspection

### `switch-service/app.py`
- **Purpose**: Entry point for clients - routes traffic through the NFV chain
- **Endpoint**: `POST /route` - receives client request
- **Logic**:
  1. Receives client request
  2. Forwards to `http://firewall-service:5000/check` (inter-service HTTP call)
  3. Sends log to `http://monitor-service:5002/log` (fire-and-forget)
  4. Returns firewall's response to the client
- **Error handling**: Returns 503 if firewall is down, silently ignores monitor failures
- **Key learning**: Service-to-service communication, `requests` library, error handling

### `monitor-service/app.py`
- **Purpose**: Centralized logging service - records all traffic
- **Endpoint**: `POST /log` - receives log data (IP, message, status)
- **Logic**:
  1. Logs to console via Python `logging` module
  2. Sends structured JSON to Logstash via TCP socket (ELK integration)
  3. Gracefully handles Logstash being unavailable
- **Key learning**: Logging best practices, TCP sockets, ELK integration

### `*/requirements.txt`
```
flask       # Web framework for REST APIs
requests    # HTTP client for inter-service calls
pytest      # Testing framework
```

### `*/tests/test_app.py`
- **Firewall tests**: Allowed request, blocked IP, 3 blocked keywords, invalid JSON, health check
- **Switch tests**: Uses `unittest.mock.patch` to mock external HTTP calls (firewall & monitor)
- **Monitor tests**: Uses `unittest.mock.patch` to mock Logstash TCP connection
- **Key learning**: Unit testing, mocking external dependencies, pytest fixtures

---

## PHASE 2: Dockerization

### What happens here:
Each service gets packaged into a Docker container with its own Python environment.

### `*/Dockerfile` (identical for all 3 services)
```dockerfile
FROM python:3.9       # Step 1: Use official Python base image
WORKDIR /app          # Step 2: Set working directory
COPY . .              # Step 3: Copy source code into container
RUN pip install -r requirements.txt   # Step 4: Install dependencies
CMD ["python", "app.py"]              # Step 5: Run the app when container starts
```

### How to build and test:
```bash
# Build each service
docker build -t diksha/firewall-service ./firewall-service
docker build -t diksha/switch-service ./switch-service
docker build -t diksha/monitor-service ./monitor-service

# Test individually
docker run -d -p 5000:5000 diksha/firewall-service
curl -X POST http://localhost:5000/check -H "Content-Type: application/json" -d '{"message":"hello"}'
```

---

## PHASE 3: Docker Compose (Multi-Container Setup)

### What happens here:
All 3 services + ELK stack run together with one command.

### `docker-compose.yml` breakdown:

| Service | Port | Purpose |
|---------|------|---------|
| `firewall-service` | 5000 | Virtual firewall |
| `switch-service` | 5001 | Traffic router (entry point) |
| `monitor-service` | 5002 | Logger |
| `elasticsearch` | 9200 | Log storage & search |
| `logstash` | 5044, 5050 | Log collection & parsing |
| `kibana` | 5601 | Log visualization dashboard |

### Key configuration details:
- **`depends_on`**: Switch waits for Firewall and Monitor; Monitor waits for Logstash
- **`nfv-network`**: Custom bridge network so all services can find each other by name
- **`healthcheck`**: Docker automatically checks if services are healthy
- **`restart: unless-stopped`**: Auto-restart on crashes
- **`es-data` volume**: Elasticsearch data persists even if container is removed

### How to run:
```bash
docker-compose up -d          # Start everything
docker-compose logs -f        # Watch all logs
docker-compose down           # Stop everything

# Test the full chain:
curl -X POST http://localhost:5001/route \
  -H "Content-Type: application/json" \
  -d '{"message": "hello world"}'
# Expected: {"status": "allowed", "message": "hello world"}

curl -X POST http://localhost:5001/route \
  -H "Content-Type: application/json" \
  -d '{"message": "hack attempt"}'
# Expected: {"status": "blocked", "reason": "Contains 'hack'"}
```

---

## PHASE 4: Git & GitHub

### What happens here:
Code is version-controlled and pushed to GitHub, which triggers the CI/CD pipeline.

### Steps:
```bash
cd nfv-devops-project
git init
git add .
git commit -m "Initial commit: NFV microservices with Docker, K8s, Ansible, ELK"
git remote add origin https://github.com/YOUR_USERNAME/nfv-devops-project.git
git push -u origin main
```

### GitHub Webhook setup:
1. Go to GitHub repo → Settings → Webhooks → Add webhook
2. Payload URL: `http://YOUR_JENKINS_IP:8080/github-webhook/`
3. Content type: `application/json`
4. Events: "Just the push event"

### What this enables:
Every `git push` → GitHub sends POST to Jenkins → Pipeline triggers automatically

---

## PHASE 5: Jenkins CI/CD Pipeline

### What happens here:
Jenkins automates the entire Build → Test → Dockerize → Push → Deploy cycle.

### `Jenkinsfile` stage-by-stage:

```
┌─────────────────────────────────────────────────────────────┐
│                    JENKINS PIPELINE                          │
│                                                              │
│  Stage 1: Clone Repository                                   │
│  └─ Jenkins pulls latest code from GitHub                    │
│                                                              │
│  Stage 2: Run Tests                                          │
│  └─ pytest runs all test files for each service              │
│  └─ If ANY test fails → pipeline STOPS here                  │
│                                                              │
│  Stage 3: Build Docker Images                                │
│  └─ docker build for each service                            │
│  └─ Creates 3 tagged images (firewall, switch, monitor)      │
│                                                              │
│  Stage 4: Push to Docker Hub                                 │
│  └─ Logs in using stored credentials (docker-hub-creds)      │
│  └─ Pushes all 3 images to Docker Hub registry               │
│                                                              │
│  Stage 5: Deploy to Kubernetes                               │
│  └─ kubectl apply -f for each deployment YAML                │
│  └─ K8s pulls new images and does rolling update             │
└─────────────────────────────────────────────────────────────┘
```

### Jenkins setup prerequisites:
1. **Install Jenkins** (via Docker: `docker run -p 8080:8080 jenkins/jenkins:lts`)
2. **Install plugins**: Git, GitHub Integration, Docker Pipeline, Kubernetes CLI
3. **Add credentials**:
   - Docker Hub: Manage Jenkins → Credentials → Add → Username/Password → ID: `docker-hub-creds`
4. **Create pipeline job**:
   - New Item → Pipeline → "Pipeline script from SCM" → Git → Your repo URL
5. **Enable trigger**: Build Triggers → "GitHub hook trigger for GITScm polling"

### Credential security:
- `withCredentials([usernamePassword(...)])` injects secrets as environment variables
- Credentials are NEVER printed in logs
- Stored encrypted in Jenkins, not in code

---

## PHASE 6: Kubernetes Deployment

### What happens here:
Docker containers run as managed pods in a Kubernetes cluster with auto-healing and scaling.

### `k8s/firewall-deployment.yaml` breakdown:
- **Deployment** (manages pods):
  - `replicas: 2` → Always 2 firewall pods running
  - `RollingUpdate` strategy → Zero-downtime deployments
  - `livenessProbe` → K8s restarts pod if /health fails
  - `readinessProbe` → K8s only sends traffic when pod is ready
  - `resources` → CPU/memory limits prevent runaway containers
- **Service** (networking):
  - `ClusterIP` → Internal access only (other services call it by name)
  - DNS name `firewall-service` resolves to this service

### `k8s/switch-deployment.yaml`:
- Same as firewall but with `type: NodePort`
- `nodePort: 30001` → External clients access via `<NodeIP>:30001`
- This is the only externally-facing service

### `k8s/monitor-deployment.yaml`:
- `replicas: 1` → Only 1 monitor instance needed
- `ClusterIP` → Internal access only

### `k8s/firewall-hpa.yaml` (Advanced Feature):
- Horizontal Pod Autoscaler
- Automatically scales firewall from 2 to 10 pods
- Triggers when CPU usage exceeds 70%

### How to deploy:
```bash
# Start local K8s cluster
minikube start

# Deploy all services
kubectl apply -f k8s/

# Verify
kubectl get pods          # Should see 5 pods (2+2+1)
kubectl get services      # Should see 3 services

# Access the app
minikube service switch-service --url   # Gets the external URL

# Watch autoscaling
kubectl get hpa
```

---

## PHASE 7: Ansible Automation

### What happens here:
Instead of manually installing Docker and K8s on servers, Ansible does it automatically.

### Execution flow:
```
You run: ansible-playbook -i inventory/hosts playbooks/site.yml
         │
         ▼
    Play 1: "Setup infrastructure" → runs on ALL servers
    ├── Role: docker
    │   ├── Update apt cache
    │   ├── Install Docker dependencies
    │   ├── Install Docker
    │   ├── Start Docker service
    │   ├── Add user to docker group
    │   └── Install Docker Compose
    │
    └── Role: kubernetes
        ├── Install kubectl via snap
        ├── Download Minikube
        └── Verify installation
         │
         ▼
    Play 2: "Deploy application" → runs ONLY on k8s-master
    └── Role: deploy
        ├── Create project directory
        ├── Copy K8s manifests
        ├── kubectl apply (firewall, switch, monitor)
        └── Wait for pods to be ready
```

### Key Ansible concepts used:
- **Roles**: Modular, reusable task collections (docker, kubernetes, deploy)
- **Inventory**: Defines which servers to target
- **`become: yes`**: Run as sudo
- **`loop`**: Iterate over a list of items
- **`register`**: Capture command output for later use

### How to run:
```bash
ansible-playbook -i ansible/inventory/hosts ansible/playbooks/site.yml

# Dry run (check mode):
ansible-playbook -i ansible/inventory/hosts ansible/playbooks/site.yml --check

# Verbose mode (for debugging):
ansible-playbook -i ansible/inventory/hosts ansible/playbooks/site.yml -vvv
```

---

## PHASE 8: ELK Stack (Monitoring & Logging)

### What happens here:
All application logs are collected, stored, and visualized in real-time.

### Data flow:
```
Monitor Service (app.py)
    │
    │ TCP socket → JSON log entry
    │ {"ip": "10.0.0.1", "message": "hello", "status": "allowed", "service": "nfv-monitor"}
    │
    ▼
Logstash (logstash.conf)
    │
    │ Input: TCP port 5000, JSON codec
    │ Filter: Parse timestamp, add "application: nfv-devops" field
    │ Output: Forward to Elasticsearch
    │
    ▼
Elasticsearch (port 9200)
    │
    │ Stores in index: "nfv-logs-2026.04.17" (date-based)
    │ Full-text searchable
    │
    ▼
Kibana (port 5601)
    │
    │ Web UI → Create index pattern "nfv-logs-*"
    │ Discover tab → Search/filter logs
    │ Dashboard → Create visualizations
    └─ Pie chart: allowed vs blocked
    └─ Line chart: requests over time
    └─ Data table: blocked IPs
```

### `logstash/pipeline/logstash.conf` breakdown:
- **input**: Listens on TCP port 5000, expects JSON
- **filter**: Parses ISO8601 timestamps, adds "application" field
- **output**: Sends to Elasticsearch index `nfv-logs-YYYY.MM.dd`, also prints to stdout

### How to verify ELK is working:
```bash
# Check Elasticsearch is running
curl http://localhost:9200

# Check if logs are being indexed
curl http://localhost:9200/nfv-logs-*/_count

# Search logs
curl http://localhost:9200/nfv-logs-*/_search?q=status:blocked

# Open Kibana
# Browser → http://localhost:5601
```

---

## COMPLETE END-TO-END FLOW

Here's what happens from a code change to a running, monitored deployment:

```
1. DEVELOPER makes a code change
   └─ Adds "phishing" to BLOCKED_KEYWORDS in firewall-service/app.py

2. GIT PUSH
   └─ git add . && git commit -m "Block phishing keyword" && git push

3. GITHUB receives the push
   └─ Webhook sends POST to Jenkins

4. JENKINS PIPELINE triggers
   ├─ Stage 1: Pulls latest code from GitHub
   ├─ Stage 2: Runs pytest → all 16 tests pass ✓
   ├─ Stage 3: Builds 3 Docker images
   ├─ Stage 4: Pushes images to Docker Hub
   └─ Stage 5: kubectl apply → deploys to K8s

5. KUBERNETES performs rolling update
   ├─ Creates new pods with updated image
   ├─ Waits for readiness probe (GET /health returns 200)
   ├─ Routes traffic to new pods
   └─ Terminates old pods → ZERO DOWNTIME

6. CLIENT sends a request
   └─ curl POST http://<NodeIP>:30001/route -d '{"message": "phishing email"}'

7. REQUEST FLOWS through the NFV chain
   ├─ Switch receives request → forwards to Firewall
   ├─ Firewall detects "phishing" → returns 403 BLOCKED
   ├─ Switch logs to Monitor → Monitor records the event
   └─ Switch returns 403 to client

8. ELK captures the log
   ├─ Monitor sends JSON to Logstash via TCP
   ├─ Logstash parses and forwards to Elasticsearch
   └─ Kibana dashboard shows the blocked request in real-time

9. HPA monitors CPU
   └─ If firewall CPU > 70%, auto-scales from 2 to up to 10 pods
```

---

## MARKS MAPPING

| Component | Files | Marks |
|-----------|-------|-------|
| Working microservices | `*/app.py` | Part of 20 |
| Docker containerization | `*/Dockerfile`, `docker-compose.yml` | Part of 20 |
| Git + GitHub | Repository setup + webhooks | Part of 20 |
| Jenkins CI/CD | `Jenkinsfile` + Jenkins config | Part of 20 |
| Kubernetes deployment | `k8s/*.yaml` | Part of 20 |
| Automated tests | `*/tests/test_app.py` | Part of 20 |
| ELK Stack | `logstash.conf` + docker-compose ELK | Part of 20 |
| Ansible automation | `ansible/` directory | Part of 20 |
| **Ansible Roles** | `ansible/roles/` | **3 marks (Advanced)** |
| **Kubernetes HPA** | `k8s/firewall-hpa.yaml` | **3 marks (Advanced)** |
| **Rolling Updates** | `strategy: RollingUpdate` in K8s | **2 marks (Innovation)** |
| **Health Checks** | Liveness + Readiness probes | **2 marks (Innovation)** |

---

## QUICK COMMANDS REFERENCE

```bash
# === Local Development ===
cd nfv-devops-project
docker-compose up -d                    # Start everything
docker-compose logs -f                  # Watch logs
docker-compose down                     # Stop everything

# === Testing ===
cd firewall-service && python -m pytest tests/ -v
cd switch-service && python -m pytest tests/ -v
cd monitor-service && python -m pytest tests/ -v

# === Git ===
git add . && git commit -m "message" && git push

# === Kubernetes ===
minikube start
kubectl apply -f k8s/
kubectl get pods
kubectl get services
kubectl logs <pod-name>

# === Ansible ===
ansible-playbook -i ansible/inventory/hosts ansible/playbooks/site.yml

# === Test API ===
curl -X POST http://localhost:5001/route -H "Content-Type: application/json" -d '{"message":"hello"}'
curl -X POST http://localhost:5001/route -H "Content-Type: application/json" -d '{"message":"hack"}'

# === ELK ===
curl http://localhost:9200                          # Check Elasticsearch
curl http://localhost:9200/nfv-logs-*/_count        # Count logs
# Browser → http://localhost:5601                   # Kibana dashboard
```
