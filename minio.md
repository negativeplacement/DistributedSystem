# Distributed MinIO Storage Cluster

This project deploys a **Distributed Object Storage System** using MinIO and Docker Compose. It simulates a production-grade cloud storage environment locally on your machine, capable of withstanding node failures while keeping data accessible.

## Architecture

The system consists of **4 Storage Nodes** forming a single storage mesh using **Erasure Coding**. An **Nginx Load Balancer** sits in front of the cluster to distribute traffic and handle failover.

* **Load Balancer:** Nginx (Proxying API on `:9000` and Console on `:9001`)
* **Storage Nodes:** `minio1`, `minio2`, `minio3`, `minio4`
* **Data Protection:** Erasure Coding (Allows the loss of up to 2 nodes while keeping data safe)
* **Storage Location:** Mapped locally to `./minio-storage/` (so you can inspect the raw data shards)

## Prerequisites

* **Docker Desktop** (must be running)
* **Python 3.10+** (for the worker script)

## Setup Guide

### 1. Configuration
Ensure you have a `.env` file in the root directory. This controls your passwords and ports.
*(See the .env.example file, modify the values and then rename it to .env and save)*

### 2. Start the Infrastructure
Run the following command to spin up the 4 nodes and the load balancer:

```bash
docker-compose up -d
```

### 3. Prepare the Python Worker
Install the necessary dependencies for the ingestion script:

```bash
pip install -r requirements.txt
```

## Usage (Ingesting Data)

1. **Prepare your Data**
Place the files you want to upload inside the `my_dataset` folder (or whichever folder you defined in `.env` as `LOCAL_DATA_FOLDER`).

2. **Run the Worker**
Execute the script to create the bucket and upload your files:
```bash
python ingest.py
```
    * The script will connect to the Load Balancer (localhost:9000)
    * It will automatically distribute the files across the 4 nodes


##Verification

**Option A: The Web Console**
1. Open your browser to `http://localhost:9001`.
2. Login with the credentials from your .env file (Default: admin / securepassword123).
3. Browse the Bucket to see your uploaded files.

**Option B: The File System**
MinIO doesn't store the files as-is. They are split into shards (x1.meta)
1. Open your project folder.
2. Navigate to `minio-storage/node1/lake-data/`.
3. Observe that the original file is replaced by xl.meta.
4. Check node2, node3, and node4 to see that the data exists simultaneously on all drives.


## Fault Tolerance Testing ("Chaos Mode")

To demonstrate the system's resilience (Erasure Coding), follow these steps to simulate server failures.

### Test 1: Simulate a Single Node Failure

1. **Kill one container** (simulating a server crash):

   ```bash
   docker stop minio1
   ```
### Verify Availability
1. Go to the Web Console (`http://localhost:9001`) and refresh the page.
2. **Observation:** The system remains fully operational. You can still browse, download, and upload files.
3. **Why:** Nginx automatically detects the dead node and routes traffic to the remaining 3 nodes.

### Test 2: Simulate Critical Failure (2 Nodes Down)
1. **Kill a second container** (simulating a cluster-wide disaster):
   ```bash
   docker stop minio2 
   ```
2. **Read Test (Success)**
    * Try to download a file via the Console or run a read script.

    * Result: Success. You only need N/2 nodes (2 nodes) to read data.
3. **Write Test (Failure)**
    * Try to upload a new file.
    * Result: Blocked. Write operations require N/2 + 1 nodes (3 nodes) to prevent "split-brain" data corruption.

### Test 3: Recovery (Self-Healing)
1. **Bring the nodes back online:**
```bash
docker start minio1 minio2
```
2. **Observation:** MinIO automatically detects the peers returning. It will sync any data that changed while they were offline (though in this test, no data changed). The cluster returns to "Green" status.

## Cleanup
To stop the cluster and remove all containers/networks
```bash
docker-compose down
```
To wipe all data and start completely fresh (deletes the local storage folders):
```bash
rm -rf ./minio-storage
```