from django.shortcuts import render
from django.http import JsonResponse
import requests


def chat_view(request):
    return render(request, "chat.html")


# ==============================
# GITHUB ANALYSIS USING API
# ==============================

def analyze_repo(repo_url):

    try:
        repo_url = repo_url.replace(".git", "").strip("/")
        parts = repo_url.split("/")
        user = parts[-2]
        repo = parts[-1]
    except:
        return {"invalid": True}

    # 1️⃣ Get default branch
    repo_api = f"https://api.github.com/repos/{user}/{repo}"
    repo_data = requests.get(repo_api)

    if repo_data.status_code != 200:
        return {"invalid": True}

    default_branch = repo_data.json().get("default_branch", "main")

    # 2️⃣ Get complete tree of default branch
    tree_api = f"https://api.github.com/repos/{user}/{repo}/git/trees/{default_branch}?recursive=1"
    tree_data = requests.get(tree_api)

    if tree_data.status_code != 200:
        return {"invalid": True}

    files = tree_data.json().get("tree", [])
    filenames = [file["path"].lower() for file in files]

    # =============================
    # TECHNOLOGY PRIORITY ORDER
    # =============================

    # 1️⃣ .NET
    if any(name.endswith(".csproj") for name in filenames):
        return {"type": "dotnet"}

    # 2️⃣ Java
    if any(name.endswith("pom.xml") for name in filenames) or any(name.endswith("build.gradle") for name in filenames):
        return {"type": "java"}

    # 3️⃣ Docker
    if any("dockerfile" in name for name in filenames):
        return {"type": "docker"}

    # 4️⃣ Python
    if any("requirements.txt" in name for name in filenames):
        return {"type": "python"}

    # 5️⃣ Node
    if any("package.json" in name for name in filenames):
        return {"type": "node"}

    return {"type": "standalone"}

# ==============================
# PIPELINE GENERATORS
# ==============================

def github_pipeline(script):
    formatted = "\n          ".join(script.strip().split("\n"))

    return f"""
name: Middleware Deployment

on:
  push:
    branches: [ "main" ]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Build & Deploy
        run: |
          {formatted}
"""


def jenkins_pipeline(script):
    return f"""
pipeline {{
    agent any
    stages {{
        stage('Build & Deploy') {{
            steps {{
                sh '''
{script}
                '''
            }}
        }}
    }}
}}
"""


# ==============================
# CHAT FLOW
# ==============================

def chat_response(request):
    msg = request.GET.get("msg", "").strip().lower()

    if not request.session.session_key:
        request.session.create()

    state = request.session.get("state")

    # START
    if msg == "start":
        request.session["state"] = "repo"
        return JsonResponse({"reply": "Enter GitHub repository URL"})

    # REPO STEP
    if state == "repo":

        analysis = analyze_repo(msg)
        request.session["analysis"] = analysis

        if analysis["type"] == "docker":
            request.session["state"] = "container"
            return JsonResponse({"reply": "Dockerfile detected. Docker or Kubernetes?"})

        if analysis["type"] == "dotnet":
            request.session["server"] = "iis"
            request.session["state"] = "pipeline"
            return JsonResponse({"reply": ".NET detected → IIS selected automatically.\nGitHub Actions or Jenkins?"})

        if analysis["type"] == "java":
            request.session["state"] = "java_server"
            return JsonResponse({"reply": "Java detected.\nSelect server: Tomcat or Apache?"})

        request.session["state"] = "pipeline"
        return JsonResponse({"reply": "Standalone deployment.\nGitHub Actions or Jenkins?"})

    # JAVA SERVER
    if state == "java_server":
        if "tomcat" in msg:
            request.session["server"] = "tomcat"
        elif "apache" in msg:
            request.session["server"] = "apache"
        else:
            return JsonResponse({"reply": "Type Tomcat or Apache"})

        request.session["state"] = "pipeline"
        return JsonResponse({"reply": "GitHub Actions or Jenkins?"})

    # CONTAINER STEP
    if state == "container":
        if "docker" in msg:
            request.session["container"] = "docker"
        elif "kubernetes" in msg:
            request.session["container"] = "kubernetes"
        else:
            return JsonResponse({"reply": "Type Docker or Kubernetes"})

        request.session["state"] = "pipeline"
        return JsonResponse({"reply": "GitHub Actions or Jenkins?"})

    # PIPELINE STEP
    if state == "pipeline":

        if "github" in msg:
            tool = "github"
        elif "jenkins" in msg:
            tool = "jenkins"
        else:
            return JsonResponse({"reply": "Type GitHub Actions or Jenkins"})

        analysis = request.session.get("analysis")
        server = request.session.get("server")
        container = request.session.get("container")

        # DEPLOYMENT LOGIC

        if analysis["type"] == "docker":

            if container == "docker":
                script = """
docker build -t myapp .
docker push user/myapp
ssh user@middleware "docker pull user/myapp && docker run -d -p 80:80 user/myapp"
"""
            else:
                script = """
docker build -t myapp .
docker push user/myapp
kubectl apply -f deployment.yaml
"""

        elif analysis["type"] == "dotnet":
            script = """
dotnet publish -c Release
scp -r publish/ user@middleware:/inetpub/wwwroot/
ssh user@middleware "iisreset"
"""

        elif analysis["type"] == "java":
            if server == "tomcat":
                script = """
mvn clean package
scp target/app.war user@middleware:/opt/tomcat/webapps/
ssh user@middleware "systemctl restart tomcat"
"""
            else:
                script = """
mvn clean package
scp target/app.war user@middleware:/var/www/html/
ssh user@middleware "systemctl restart apache2"
"""

        else:
            script = """
Build application
scp -r build/ user@middleware:/opt/app/
ssh user@middleware "systemctl restart app"
"""

        pipeline = github_pipeline(script) if tool == "github" else jenkins_pipeline(script)

        request.session["state"] = None

        return JsonResponse({"reply": f"<pre>{pipeline}</pre>"})

    return JsonResponse({"reply": "Type start to begin"})
