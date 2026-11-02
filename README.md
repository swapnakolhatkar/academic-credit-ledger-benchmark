Markdown

````
# Range-Based Geo-Partitioning and Distributed SQL Architecture for High-Throughput Academic Credit Ledgers

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![CockroachDB](https://img.shields.io/badge/CockroachDB-v23.1%2B-orange.svg)](https://www.cockroachlabs.com/)

This repository contains the official experimental codebase, schema definitions, and multi-threaded benchmarking scripts accompanying the research paper:
> **"Range-Based Geo-Partitioning and Distributed SQL Architecture for High-Throughput Academic Credit Ledgers"**

---

## 🏗️ Architectural Overview

National-scale educational digital public infrastructure—such as India's Automated Permanent Academic Account Registry (APAAR ID) and Academic Bank of Credits (ABC)—demands high-availability transactional storage capable of surviving sudden regional traffic spikes (e.g., annual examination result declarations). 

This project implements a containerized **3-node distributed SQL cluster** using **CockroachDB**, governed by:
1. **Raft Consensus Protocol:** Ensures multi-active synchronous replication and fault tolerance across regional nodes without single-master bottlenecks.
2. **Range-Based Geo-Partitioning:** Dynamically shards and pins table ranges based on state attributes (`state_code`), guaranteeing local data access routing and eliminating cross-region latency.

---

## 📁 Repository Structure

```text
├── benchmark_concurrent.py     # Multi-threaded benchmark runner for Workload A (Read-Heavy)
├── benchmark_workload_b.py     # Multi-threaded benchmark runner for Workload B (Write-Heavy)
├── requirements.txt            # Python dependencies (psycopg2-binary, faker)
└── README.md                   # Repository documentation & usage guide
````

## **🚀 Getting Started & Replication Guide**

### **Prerequisites**

* **Docker & Docker Compose** (for running the multi-node distributed database cluster)  
* **Python 3.8+**

### **Step 1: Spin Up the 3-Node Distributed CockroachDB Cluster**

Deploy a secure, containerized multi-node local testbed using Docker:

Bash

```
# Create a dedicated Docker network
docker network create cockroach-net

# Start Node 1
docker run -d --name=roach-node1 --net=cockroach-net \
  -p 26257:26257 -p 8080:8080 \
  cockroachdb/cockroach:latest start-single-node \
  --insecure
```

### **Step 2: Install Python Dependencies**

Clone this repository and install the required packages:

Bash

```
git clone [https://github.com/your-username/academic-credit-ledger-benchmark.git](https://github.com/your-username/academic-credit-ledger-benchmark.git)
cd academic-credit-ledger-benchmark
pip install -r requirements.txt
```

## **📊 Running the Benchmarks**

The benchmarking suite simulates realistic national educational workloads utilizing thread-isolated connection pools via concurrent.futures.ThreadPoolExecutor.

### **1\. Workload A: Read-Heavy Profile (Credential Verification)**

Simulates background credential checks and verification lookups by employers/universities (90% read / 10% write distribution).

Bash

```
python benchmark_concurrent.py
```

### **2\. Workload B: Write-Heavy Profile (Peak Examination Season)**

Simulates peak national examination grading uploads and batch credit updates (70% write / 30% read distribution) scaling up to **200 concurrent client threads**.

Bash

```
python benchmark_workload_b.py
```

## **📈 Empirical Performance Summary**

| Workload Profile | Concurrent Threads | Total Transactions | Throughput (TPS) | Serialization Failures (40001) |
| :---- | :---- | :---- | :---- | :---- |
| **Workload A (Read-Heavy)** | 10 | 300 | **205.66** | 0 |
| **Workload A (Read-Heavy)** | 50 | 300 | **273.15** | 0 |
| **Workload A (Read-Heavy)** | 100 | 300 | **287.75** | 0 |
| **Workload B (Write-Heavy)** | 100 | 600 | **202.16** | 0 |
| **Workload B (Write-Heavy)** | 200 | 600 | **272.96** | 0 |

## **📚 Citation**

If you use this codebase or benchmarking methodology in your research, please cite our paper:

Code snippet

```
@article{RangeGeoPartitioning2026,
  title={Range-Based Geo-Partitioning and Distributed SQL Architecture for High-Throughput Academic Credit Ledgers},
  author={Your Name and Collaborators},
  journal={Journal / Conference Name},
  year={2026}
}
```

## **📝 License**

This project is licensed under the terms of the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).

&nbsp;
# academic-credit-ledger-benchmark
Empirical benchmarking scripts and schema definitions for geo-partitioned distributed SQL academic credit ledgers
