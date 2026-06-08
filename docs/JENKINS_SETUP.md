# Jenkins setup (beginner)

GitHub user: **vedanti06**  
Docker Hub user: **vd0610**

Pipeline does 3 things: **pull code → build & push images → deploy K8s manifests**.

---

## Part A — Create GitHub repo (one time)

1. Go to https://github.com/new
2. Repository name: `Video_to_mp3` (already created: https://github.com/vedanti06/Video_to_mp3)
3. Public → **Create repository** (do not add README — you already have code)
4. In PowerShell:

```powershell
cd c:\Users\vedud\OneDrive\Desktop\microservices-python

git remote remove origin
git remote add origin https://github.com/vedanti06/Video_to_mp3.git

git add .
git commit -m "Initial commit with Jenkins pipeline"
git push -u origin master
```

If your branch is `main`, use `git push -u origin main`.

---

## Part B — Start Jenkins (one time)

```powershell
cd c:\Users\vedud\OneDrive\Desktop\microservices-python
docker compose -f jenkins/docker-compose.yml up -d
```

Open **http://localhost:9090**

Get setup password:

```powershell
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

- Install **suggested plugins**
- Create admin user

Install Docker + kubectl inside Jenkins:

```powershell
docker exec -u root jenkins bash -c "apt-get update && apt-get install -y docker.io kubectl"
```

---

## Part C — One credential in Jenkins

**Manage Jenkins → Credentials → (global) → Add Credentials**

| Field | Value |
|-------|--------|
| Kind | Username with password |
| ID | `dockerhub` |
| Username | `vd0610` |
| Password | Docker Hub **access token** from https://hub.docker.com/settings/security |

---

## Part D — Create the job (one time)

1. **New Item** → name `microservices-python` → **Pipeline** → OK
2. Scroll to **Pipeline**:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/vedanti06/Video_to_mp3.git`
   - Branch: `*/master` (or `*/main`)
   - Script Path: `Jenkinsfile`
3. **Save**
4. Click **Build Now**

Watch the **Console Output** for each stage.

---

## Part E — Before deploy works

Start Minikube and MySQL on your PC:

```powershell
minikube start
kubectl get nodes
```

Then run the Jenkins job again (or only the Deploy stage will fail until Minikube is up).

After a successful deploy, expose the app:

```powershell
kubectl port-forward svc/gateway 8080:8080
```

---

## What each file does

| File | Role |
|------|------|
| `Jenkinsfile` | Pipeline: checkout → build/push → deploy |
| `scripts/jenkins-deploy.sh` | `kubectl apply` for rabbit, mongo, auth, gateway, convertor |
| `jenkins/docker-compose.yml` | Runs Jenkins locally |

---

## Common problems

| Error | Fix |
|-------|-----|
| `push access denied` | Fix `dockerhub` credential — use access token, not account password |
| `docker: not found` | Run the `apt-get install docker.io` command in Part B |
| `kubectl: not found` | Run the same command (includes kubectl) |
| Deploy cannot reach cluster | Run `minikube start`; check `%USERPROFILE%\.kube\config` exists |

---

## Later (optional)

- **Auto-build on git push:** GitHub webhook or Poll SCM — skip until the manual build works
- **Private repo:** Add GitHub credentials in Jenkins job settings
