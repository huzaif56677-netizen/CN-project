This does not work on latest python so the process is different. You can follow this -
```
# Install Python 3.10 package and venv module
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# Navigate to your project folder
cd ~/Documents/cnproject

# Create and activate Python 3.10 virtualenv
python3.10 -m venv venv
source venv/bin/activate
```
Then
```
# 1. Downgrade setuptools to enable legacy easy_install hooks
pip install --upgrade "setuptools<58.0.0" wheel

# 2. Install Ryu and WebOb
pip install git+https://github.com/faucetsdn/ryu.git webob "tinyrpc==1.0.4"

# 3. Force-install eventlet 0.33.3 (fixes Python 3.10 TimeoutError crash)
pip install "eventlet==0.33.3" --no-deps --force-reinstall
```
Verify ryu-manager works - 
```
ryu-manager --version
```
Clear state
```
sudo mn -c
```
Start the SDN controller
```
cd ~/cnproject
source venv/bin/activate
ryu-manager sdn_controller.py
```
In another terminal, using the same venv, do
```
cd ~/cnproject
sudo python3 custom_topo.py
```
Mininet will start in that terminal.
You can do ping the server from the client by typing
```
mininet> h1 ping -c 5 h2
```

For a more extensive run, do 
```
mininet> xterm h1 h2
```
inside h2:
```
python3 udp_server.py
```
inside h1:
```
python3 udp_client.py
```

The results will show for 100 packets.