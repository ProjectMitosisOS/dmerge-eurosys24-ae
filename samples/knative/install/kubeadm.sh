rm -rf $HOME/.kube
sudo kubeadm init --image-repository='registry.cn-hangzhou.aliyuncs.com/google_containers' --pod-network-cidr=10.244.0.0/16

mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config

kubectl apply -f yaml/kube-flannel.yaml

echo "done"
