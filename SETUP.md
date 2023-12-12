# Capture the kube

Disclaimer: Due to this room running on a VM it uses minikube which is not exactly the same as running a fully fledged Kubernetes cluster so you might experience some minor differences with a real cluster.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [MiniKube](https://minikube.sigs.k8s.io/docs/start/)
- [Kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)

## Setup

### Building the web application: Application readyness checker

```bash
docker build -t leofvo/demo-k8s-pentesting:1.0 ./app
docker push leofvo/demo-k8s-pentesting:1.0
```

### Provisioning the cluster

```bash
kind create cluster --name grafana-lfi
kubectl apply -f  ./k8s/
# expose the web application on port 8080 of your computer
kubectl port-forward deployment/webapp 8080 8080
```

## Notes

### Deploying Grafana to Kubernetes and configure it

- The configuration defines a ServiceAccount named grafana-sa.
- It also creates a ClusterRole named grafana-cluster-admin with permissions to manage pods, services, configmaps, and secrets. Modify these permissions according to your requirements.
- A ClusterRoleBinding associates the ServiceAccount grafana-sa with the grafana-cluster-admin role within the default namespace.
- Finally, a Grafana Deployment is defined, using the grafana-sa ServiceAccount for the Grafana pod.

**To access the Grafana dashboard:**

Apply this YAML configuration to your Kubernetes cluster using kubectl apply -f grafana-config.yaml.

After the Grafana pod is up and running, you can port-forward to the Grafana service to access the dashboard locally:

```bash
kubectl port-forward service/grafana 3000:3000
```

Open a web browser and navigate to [http://localhost:3000](http://localhost:3000) to access the Grafana dashboard.
