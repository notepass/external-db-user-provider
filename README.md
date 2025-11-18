# docker-build-test

A repository containing a complete pipeline to build and deploy a Docker container with a Python script that interfaces with the Kubernetes API to create resources from Custom Resource Definitions (CRDs).

## Features

- **Python Kubernetes CRD Manager**: A Python script (`k8s_crd_manager.py`) that provides functions to interact with Kubernetes Custom Resource Definitions
- **Docker Container**: Fully containerized application with all dependencies included
- **GitHub Actions CI/CD**: Automated build and deployment pipeline to GitHub Container Registry
- **Production Ready**: Includes proper error handling, logging, and configuration management

## Components

### 1. Python Script (`k8s_crd_manager.py`)

The main application that provides functions to:
- Create custom resources from CRDs
- Retrieve custom resources
- Delete custom resources
- List custom resources in a namespace
- Automatically detect and load Kubernetes configuration (in-cluster or local kubeconfig)

### 2. Dockerfile

Multi-stage Dockerfile that:
- Uses Python 3.11 slim base image
- Installs all required dependencies
- Copies the application files
- Sets up the proper entrypoint

### 3. GitHub Actions Workflow (`.github/workflows/docker-build.yml`)

Automated CI/CD pipeline that:
- Triggers on push to main/master branches and pull requests
- Builds the Docker image
- Pushes to GitHub Container Registry (ghcr.io)
- Tags images appropriately (branch name, PR number, SHA, latest)
- Uses Docker layer caching for faster builds

## Usage

### Running Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the script (requires Kubernetes cluster access):
```bash
python3 k8s_crd_manager.py
```

### Building the Docker Image

```bash
docker build -t k8s-crd-manager .
```

### Running the Docker Container

```bash
# With local kubeconfig
docker run -v ~/.kube:/root/.kube k8s-crd-manager

# In a Kubernetes cluster (uses in-cluster config)
kubectl run k8s-crd-manager --image=ghcr.io/notepass/docker-build-test:latest
```

### Pulling from GitHub Container Registry

After the GitHub Actions workflow runs successfully, pull the image:

```bash
docker pull ghcr.io/notepass/docker-build-test:latest
```

## Requirements

- Python 3.11+
- Kubernetes cluster access
- Docker (for building/running containers)

## Dependencies

- `kubernetes>=28.1.0` - Official Kubernetes Python client
- `PyYAML>=6.0.1` - YAML parsing for Kubernetes manifests

## Development

The repository structure:
```
.
├── .github/
│   └── workflows/
│       └── docker-build.yml    # GitHub Actions workflow
├── k8s_crd_manager.py          # Main Python application
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container definition
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## GitHub Actions Workflow

The workflow automatically:
1. Checks out the code
2. Sets up Docker Buildx for advanced build features
3. Logs in to GitHub Container Registry
4. Extracts metadata and generates appropriate tags
5. Builds and pushes the Docker image with caching enabled

The workflow runs on:
- Push to main/master branches
- Pull requests to main/master branches
- Manual trigger via workflow_dispatch

## License

MIT