## Pits-and-Falls

When conducting the experiments, there are a bunch of small details need to be **take great care of**.

#### 1. Device plugin

#### 1.1 Configuration

Now we use the image `caribouf/k8s-hostdev-plugin:0.1` for mounting the `dmerge` kernel module device into the k8s container and take it as a **resource**. So that in the `yaml ` files, we have to add the resource limitation for device mounting. 

Example is shown as below:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: my-knative-app
  namespace: default
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/min-scale: "1"
    spec:
      containers:
        - name: dmerge-p2p
          image: caribouf/dmerge-p2p
          resources:
            limits:
              hostdev.k8s.io/dev_mitosis-syscalls: 1 # dedicate the device allocation amount
          imagePullPolicy: Always
```



#### 1.2 The order of `insmod` and plugin apply

Great attention： 

***We must first do `insmod` before executing `kubectl apply -f device-plugin.yaml` !!!***.  Otherwise, the device plugin will first create a **directory** for the device path. And we can not open this device any more unless we manually delete the path.



What we should do after a machine reboot ? 

In this scenerio, the device path would be created automatically by the device and it would be definitly a **directory**. So that we have to execute `kubectl delete -f device-plugin.yaml` first, and manually delete the device path. 

Then we can directly `insmod` the kernel module and apply the device plugin into our knative cluster.