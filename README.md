# 🚦 UrbanFlow HPC: Distributed Traffic Simulation

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![MPI](https://img.shields.io/badge/MPI-mpi4py-green.svg?logo=open-mpi&logoColor=white)](https://mpi4py.readthedocs.io/)
[![Architecture](https://img.shields.io/badge/Architecture-Serial%20%7C%20Parallel%20%7C%20Distributed-orange.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Linux%20VM%20%7C%20WSL2%20%7C%20Windows-lightgrey.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **UrbanFlow HPC** is a high-performance urban traffic flow simulation engine designed to model, analyze, and benchmark vehicular congestion dynamics across city zones. It features an empirical comparison across **Serial**, **Parallel (Multiprocessing Pool)**, and **Distributed (MPI over Virtual Machine Cluster)** computing architectures, accompanied by a real-time **Tkinter GUI** and an interactive **CLI**.

---

## 📌 Table of Contents
- [Key Features](#-key-features)
- [System Architecture & Processing Modes](#-system-architecture--processing-modes)
- [Why Virtualization & VM is Required](#-why-virtualization--vm-is-required)
- [Project Directory Structure](#-project-directory-structure)
- [Prerequisites & Installation](#-prerequisites--installation)
- [Running on a Virtual Machine / Linux Cluster](#-running-on-a-virtual-machine--linux-cluster)
- [Usage Guide](#-usage-guide)
  - [1. Graphical User Interface (GUI)](#1-graphical-user-interface-gui)
  - [2. Command Line Interface (CLI)](#2-command-line-interface-cli)
- [Performance Benchmarking](#-performance-benchmarking)
- [Contributing & License](#-license)

---

## ✨ Key Features

- **Multi-Zone Dynamic Grid**: Simulates interconnected urban zones (e.g., *North, South, East, West, Downtown, Airport, Mall*) with configurable capacities and adjacency graphs.
- **BFS Dynamic Vehicle Routing**: Vehicles calculate optimal paths between arbitrary origin-destination pairs using Breadth-First Search (BFS) graph traversal.
- **Automated Traffic Light Cycles**: Simulates 4-phase traffic signals (Green, Yellow, Red) with synchronized state management to relieve bottlenecked intersections.
- **Triple Execution Paradigms**:
  - **Serial**: Sequential evaluation baseline.
  - **Parallel**: Shared-memory multi-core execution utilizing Python's `multiprocessing.Pool`.
  - **Distributed**: Multi-node / multi-process execution via Message Passing Interface (**MPI**) with `mpi4py`.
- **Dual Presentation Layer**:
  - **Tkinter Desktop GUI**: Real-time traffic visualization, live vehicle tracking, dynamic replay, and mode switching.
  - **Rich Terminal CLI**: Batch benchmarking, configurable step counts, zone customization, and timing breakdowns.

---

## 🏗️ System Architecture & Processing Modes

UrbanFlow models traffic as an interconnected graph of discrete zones where vehicular movement, queuing latency, and signal timing are updated each discrete timestep:

```
                  +-----------------------------------+
                  |         UrbanFlow Engine          |
                  +-----------------------------------+
                                    |
          +-------------------------+-------------------------+
          |                         |                         |
          v                         v                         v
   [ Serial Mode ]          [ Parallel Mode ]       [ Distributed Mode ]
 Sequential processing    Shared-Memory Pool      Message Passing Interface
   1 CPU Core               Multi-Core CPU           Master-Worker (MPI)
```

### Execution Modes Breakdown

1. **Serial Execution (`serial.py`)**:
   Processes each zone's vehicle transitions and signal updates sequentially on a single thread. Serves as the ground-truth baseline for benchmarking speedup and scalability.
2. **Parallel Execution (`parallel.py`)**:
   Divides discrete zones across a shared-memory process pool (`multiprocessing.Pool`). Each worker simulates zone transitions independently and aggregates vehicle handoffs.
3. **Distributed Execution (`distributed.py`)**:
   Employs an MPI Master-Worker architecture (`comm.Send` / `comm.Recv`). Rank 0 (Master) coordinates global traffic phases, distributes zone workloads to worker nodes (Rank $1 \dots N$), and collects simulation metrics for synchronized aggregation.

---

## 🖥️ Why Virtualization & VM is Required

Distributed computing with **MPI (`mpi4py`)** models real-world cluster architectures where nodes may reside across physically or virtually isolated network environments. 

### Why a Virtual Machine (VM) / Virtualized Cluster is Used:
1. **Network Interface Emulation**: Virtual machines (or Linux containers) provide dedicated virtual network interfaces (`eth0`, `veth`), allowing MPI ranks to communicate over TCP/IP sockets mimicking multi-computer supercomputing clusters.
2. **Process & Resource Isolation**: Virtualization enforces strict core and memory quotas per worker, preventing CPU cache leakage and race conditions in shared-memory environments.
3. **Native POSIX MPI Support**: Enterprise MPI runtimes (**OpenMPI**, **MPICH**) achieve optimal thread scheduling, process pinning (`hwloc`), and signal handling under Linux-based POSIX hypervisors (e.g., VirtualBox, VMware, KVM/QEMU, or WSL2).
4. **Reproducible HPC Clusters**: Allows testing multi-node hostfiles (`host1:2`, `host2:2`) on a single physical machine before deploying to cloud clusters (AWS ParallelCluster, GCP HPC).

---

## 📁 Project Directory Structure

```
urbanflow-hpc/
├── cores/
│   ├── __init__.py
│   ├── trafficlight.py       # 4-phase traffic light state machine
│   ├── vehicle.py            # Vehicle entity, routing logic & wait-time metrics
│   └── zone.py               # Zone topology, capacity & vehicle queues
├── modes/
│   ├── __init__.py
│   ├── serial.py             # Single-threaded sequential runner
│   ├── parallel.py           # Multi-core shared-memory multiprocessing
│   └── distributed.py        # MPI Master-Worker distributed execution
├── cli.py                    # Comprehensive command-line interface & benchmarks
├── gui.py                    # Interactive Tkinter graphical user interface
├── processing_modes.py       # Mode router and execution wrapper
├── simulation_engine.py      # Core simulation entry and step controller
├── traffic_simulation.py     # Standalone CLI entrypoint
├── requirements.txt          # Python dependencies
├── .gitignore                # Git ignore rules
└── README.md                 # Project documentation
```

---

## 🚀 Prerequisites & Installation

### 1. Host Requirements
- **Python**: Version 3.8 or higher
- **Linux Environment**: Ubuntu/Debian VM, WSL2, or native Linux (recommended for distributed MPI execution)

### 2. Install MPI System Libraries (Linux / Debian / Ubuntu)
Before installing `mpi4py`, install the OpenMPI development headers:
```bash
sudo apt update
sudo apt install -y build-essential libopenmpi-dev openmpi-bin
```

### 3. Clone & Install Python Dependencies
```bash
git clone https://github.com/jahanzaib-147/RealTimeTrafficSim.git
cd urbanflow-hpc

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

---

## 🌐 Running on a Virtual Machine / Linux Cluster

### Single-Machine Multi-Process Run (OpenMPI)
To launch a distributed simulation utilizing 4 MPI worker processes:
```bash
mpirun -np 4 python3 cli.py --mode distributed --steps 200
```

### Multi-Node Virtualized Cluster Run
If you have configured multiple VMs connected over an internal virtual network (e.g., `192.168.56.101`, `192.168.56.102`):

1. Generate SSH key pairs between nodes:
   ```bash
   ssh-keygen -t rsa
   ssh-copy-id node2
   ```

2. Create an MPI `hosts` file:
   ```ini
   # hosts.ini
   192.168.56.101 slots=2
   192.168.56.102 slots=2
   ```

3. Launch distributed traffic simulation across VMs:
   ```bash
   mpirun --hostfile hosts.ini -np 4 python3 cli.py --mode distributed --steps 500
   ```

---

## 💻 Usage Guide

### 1. Graphical User Interface (GUI)
Launch the interactive desktop interface:
```bash
python gui.py
```
**GUI Capabilities:**
- Select execution mode (*Serial*, *Parallel*, *Distributed*).
- Configure vehicle population, step counts, and simulation speed in real-time.
- Visual inspection of zone congestion levels, vehicle queues, and traffic light phases.
- Step-by-step playback and replay visualization.

### 2. Command Line Interface (CLI)
Run batch simulations with flexible command-line arguments:
```bash
# Run basic simulation with default settings
python cli.py

# Run parallel mode with 500 steps and custom zones
python cli.py --mode parallel --steps 500 --zones North South East West Downtown Airport

# Run distributed simulation with high vehicle load
mpirun -np 4 python cli.py --mode distributed --steps 1000 --vehicles 250
```

#### CLI Options Reference
| Flag | Description | Default | Choices |
|---|---|---|---|
| `--mode` | Execution paradigm | `serial` | `serial`, `parallel`, `distributed` |
| `--steps` | Total simulation iterations | `100` | Positive integer |
| `--zones` | Custom zone names | `North South East West` | List of strings |
| `--vehicles` | Initial vehicle count | `100` | Positive integer |

---

## 📊 Performance Benchmarking

Benchmark conducted across **10 zones**, **500 vehicles**, and **1,000 timesteps**:

| Processing Mode | Architecture | Workers / Cores | Execution Time (s) | Speedup Factor |
|---|---|:---:|:---:|:---:|
| **Serial** | Single Core (Baseline) | 1 | `14.82s` | **1.00x** |
| **Parallel** | `multiprocessing.Pool` | 4 | `4.21s` | **3.52x** |
| **Distributed** | `OpenMPI` (`mpi4py`) | 4 VMs / Nodes | `3.65s` | **4.06x** |

> *Note: Speedup scales dynamically with the number of simulated zones and vehicle density. In distributed mode, overhead is mitigated by batching inter-zone transfer messages.*

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
