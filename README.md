# Serialization/Deserialization-free State Transfer in Serverless Workflows with RDMA-based Remote Memory Map

## 1. Project introduction

One set of distributed OS primitives that transparently merge (or reduce) arbitrary data structure in DAG workflow.

Submodule versions: 

- MITOSIS: [cef994](https://ipads.se.sjtu.edu.cn:1312/distributed-rdma-serverless/mitosis-project/mitosis/-/commit/cef994c32580f27f730716462dd602a95bdb9c75)
- Jemalloc: 36366f

Please check carefully before updating the submodule version.

## 2. Getting start instructions

We use Knative as serverless platform and use (TODO: val05) as the master node, and we have two more servers as worker nodes. First you need to clone project code on master node.  We say the `val05` as both master node in knative and control node for building. 

> We'll give the server name and password to you

```bash
# On val05
cd $HOME
mkdir -p $HOME/projects
git clone https://github.com/<TODO> $HOME/projects/dmerge
cd $HOME/projects/dmerge
git config --global http.sslverify false
git submodule update --init --recursive
git checkout artifact-eurosys24

export PROJECT_PATH=$HOME/projects/dmerge
```

Then you need to ensure val05 can use `ssh` protocol to other two worker nodes. Use `ssh-keygen` and  `ssh-copy-id` command to finish this configuration.

```sh
# On val05
ssh-keygen # generate rsa key
ssh-copy-id $USER@val06
ssh-copy-id $USER@val07
```



## 3. kick-the-tires

### 3.1 Kubernates configuration

Now the kubernates has been configured, and you only need to copy the kubernates config files to your user path.

```sh
# On val05
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

Check the configuration result by executing:

```sh
# On val05
$ kubectl get nodes

NAME    STATUS   ROLES                  AGE   VERSION
val05   Ready    control-plane,master   11d   v1.23.5
val06   Ready    <none>                 11d   v1.23.5
val07   Ready    <none>                 11d   v1.23.5
```



### 3.2 Essential software installation

Some software dependencies shall be installed before compiling the project. You only need to install these on **master** node.

#### Clang 

Install clang by executing commands as below:

```bash
# get source code
wget https://releases.llvm.org/9.0.0/clang+llvm-9.0.0-x86_64-linux-gnu-ubuntu-16.04.tar.xz

# unzip the source file, rename it and add it to PATH directly. We make bash as an example.
tar -xvf clang+llvm-9.0.0-x86_64-linux-gnu-ubuntu-16.04.tar.xz
mv clang+llvm-9.0.0-x86_64-linux-gnu-ubuntu-16.04 clang-9
# Then set the PATH environment according to your downloaded path
# For example, if the clang-9 is under path ~/, set the PATH as:
#	CLANG_HOME=~/clang-9
# PATH=$CLANG_HOME/bin:$PATH
```

#### Rustup toolchain

Install rustup with nightly version as below:

```sh
curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | sh
source $HOME/.cargo/env
rustup default nightly-2022-02-04-x86_64-unknown-linux-gnu
rustup component add rust-src
```

Use `rustup toolchain list` to check the correct toolchain has been installed.

```sh
rustup toolchain list

# The output result is supposed to be:
#   stable-x86_64-unknown-linux-gnu
#   nightly-2022-02-04-x86_64-unknown-linux-gnu (default)
```

#### Python virtual dependencies

```sh
cd $PROJECT_PATH/ae_scripts
python3 -m pip install virtualenv # install virtualenv if essential
virtualenv env
source env/bin/activate
pip install -r requirements.txt
```

Then run commands below under directory `ae_scripts` to check if all dependencies are installed. You can remove all useless images via this command.

```sh
cd $PROJECT_PATH/ae_scripts
export PASSWORD="" # Change to your login password
python bootstrap.py -f clean-img.toml -u $USER -p $PASSWORD 
```



### 3.3 Build kernel module

Go to path `ae_scripts` and run command as below:

```sh
cd $PROJECT_PATH/ae_scripts
bash sync-km.sh
```

This shell shall not output any error messages, and you can go to `val06` and `val07` at path `$HOME/projects/dmerge/` to see if both `dmerge-kms` and `makefile` exist in this path.

```sh
# Take val06 as one example
ssh eurosys24ae@val06 "ls ~/projects/dmerge/"
```

Now you are onboard! And please refer to [exp.md](./docs/exp.md) for experiment evaluations.
