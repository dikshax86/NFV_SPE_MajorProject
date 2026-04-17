# Jenkins Server Setup Guide

## Your Jenkins Server: 172.16.144.220:8080

Open a terminal and SSH into your Jenkins server:

```bash
ssh ubuntu@172.16.144.220
```

(Or whatever user you use to access it)

---

## Step 1: Check What's Already Installed

Run these to see what you already have:

```bash
docker --version
ansible --version
kubectl version --client 2>/dev/null
minikube version 2>/dev/null
java -version
```

---

## Step 2: Install kubectl

kubectl is the command-line tool to interact with Kubernetes.

```bash
# Download kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# Install it
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Verify
kubectl version --client
```

---

## Step 3: Install Minikube

Minikube runs a local single-node Kubernetes cluster.

```bash
# Download Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64

# Install it
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Verify
minikube version
```

---

## Step 4: Install Ansible (if not already installed)

```bash
sudo apt update
sudo apt install -y ansible
ansible --version
```

---

## Step 5: Install conntrack (required by Minikube)

```bash
sudo apt install -y conntrack
```

---

## Step 6: Start Minikube

THIS IS THE CRITICAL STEP. Minikube needs to run as the `jenkins` user because Jenkins pipeline runs as `jenkins`.

```bash
# Switch to jenkins user
sudo su - jenkins

# Start Minikube with Docker driver
minikube start --driver=docker

# Verify cluster is running
kubectl get nodes
```

You should see output like:
```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   30s   v1.28.x
```

### If you get "permission denied" for Docker:

```bash
# Exit back to your regular user first
exit

# Add jenkins user to docker group
sudo usermod -aG docker jenkins

# Restart Jenkins service
sudo systemctl restart jenkins

# Switch back to jenkins and try again
sudo su - jenkins
minikube start --driver=docker
```

---

## Step 7: Verify Everything Works as Jenkins User

Stay as the `jenkins` user and run:

```bash
# Check Minikube
minikube status

# Check kubectl can talk to the cluster
kubectl get nodes

# Check kubectl can create resources
kubectl create namespace test-nfv
kubectl delete namespace test-nfv

# Check Docker
docker ps
```

All commands should work WITHOUT sudo.

---

## Step 8: Test a Sample Deployment

Still as `jenkins` user:

```bash
# Create a test pod
kubectl run test-pod --image=nginx --port=80

# Check it's running
kubectl get pods

# Clean up
kubectl delete pod test-pod
```

---

## Step 9: Make Minikube Start on Boot (Optional but Recommended)

If the server reboots, Minikube won't auto-start. Create a systemd service:

```bash
# Exit to regular user
exit

# Create service file
sudo tee /etc/systemd/system/minikube.service > /dev/null <<'EOF'
[Unit]
Description=Minikube
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=jenkins
ExecStart=/usr/local/bin/minikube start --driver=docker
ExecStop=/usr/local/bin/minikube stop

[Install]
WantedBy=multi-user.target
EOF

# Enable it
sudo systemctl daemon-reload
sudo systemctl enable minikube
```

---

## Step 10: Install Ansible Plugin in Jenkins (Web UI)

1. Open browser: http://172.16.144.220:8080
2. Go to: Manage Jenkins → Plugins → Available plugins
3. Search for: **Ansible**
4. Install: **Ansible plugin**
5. Restart Jenkins if prompted

### Configure Ansible in Jenkins:

1. Go to: Manage Jenkins → Tools
2. Scroll to **Ansible** section
3. Click **Add Ansible**
4. Name: `ansible`
5. Path: Run `which ansible` on server to get the path (usually `/usr/bin/`)
6. Save

---

## Troubleshooting

### "minikube: command not found" in Jenkins pipeline
The PATH might be different for jenkins user. Fix:

```bash
sudo su - jenkins
echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
source ~/.bashrc
```

### "kubectl: command not found" in Jenkins pipeline
Same fix:

```bash
sudo su - jenkins
echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
source ~/.bashrc
```

### Minikube won't start - not enough resources
Minikube needs at least 2 CPUs and 2GB RAM:

```bash
minikube start --driver=docker --cpus=2 --memory=2048
```

### "Unable to connect to the server"
Minikube stopped. Restart it:

```bash
sudo su - jenkins
minikube start --driver=docker
```

### ImagePullBackOff error in pods
Your Docker Hub images need to be public, OR add imagePullSecrets to K8s.
Easiest fix - make repos public on Docker Hub:
1. Go to hub.docker.com → Your repositories
2. Click each repo → Settings → Make Public

---

## Quick Verification Checklist

Run ALL of these as `jenkins` user (`sudo su - jenkins`):

```bash
echo "=== Docker ===" && docker --version
echo "=== kubectl ===" && kubectl version --client
echo "=== Minikube ===" && minikube status
echo "=== Ansible ===" && ansible --version
echo "=== K8s Cluster ===" && kubectl get nodes
```

All 5 should succeed. Once they do, push your code and trigger the Jenkins pipeline!
