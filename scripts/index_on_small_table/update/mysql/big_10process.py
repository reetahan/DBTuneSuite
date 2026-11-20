import os
import pymysql
import multiprocessing
import time
import csv
import random
from pathlib import Path

import numpy as np
from q1_fractal_symbols import gen

# MySQL connection details
MYSQL_DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "pwd",
    "database": os.environ["DB"],
    "charset": "utf8mb4",
}


def pick(updates, k, run_number):
    rnd = random.Random(run_number)
    hot = int(os.environ.get("HOT_KEYS", 0))
    if not hot:
        return rnd.sample(updates, k)
    rows = rnd.sample(range(len(updates)), hot)
    np.random.seed(run_number)
    pool = [rows[i] for i in gen(0.3, hot)]
    return [updates[i] for i in rnd.choices(pool, k=k)]


CSV_FILE = os.environ["CSV"]

ROOT_DIR = Path(__file__).resolve().parents[3]
RESULTS_DIR = ROOT_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_CSV = RESULTS_DIR / "mysql_index_small_update_10process.csv"


def init_results_csv():
    if not RESULTS_CSV.exists():
        with RESULTS_CSV.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["dbms", "label", "iteration", "execution_time", "response_time"])


def load_csv_data(csv_file, index_type, run_number):
    updates = []
    with open(csv_file, mode="r", newline="") as file:
        reader = csv.reader(file)
        next(reader)  # skip header
        for row in reader:
            if index_type == "clustered":
                condition_value = row[0]  # ssnum
            elif index_type == "nonclustered":
                condition_value = row[5]  # hundreds2
            else:  # scan
                condition_value = row[3]  # longitude
            modified_name = row[1] + str(run_number)
            updates.append((modified_name, condition_value))
    return updates


def update_task(process_id, index_type, updates, result_queue):
    try:
        conn = pymysql.connect(**MYSQL_DB_PARAMS, autocommit=False)
        cursor = conn.cursor()
    except pymysql.MySQLError as e:
        print(f"Process {process_id} - connection failed: {e}")
        return

    updates_count = 0

    if index_type == "clustered":
        # Use PRIMARY index on ssnum (assuming it's the PK)
        sql_template = "UPDATE employees FORCE INDEX (PRIMARY) SET name = %s WHERE ssnum = %s"
    elif index_type == "nonclustered":
        sql_template = "UPDATE employees SET name = %s WHERE hundreds2 = %s"
    else:  # scan
        sql_template = "UPDATE employees SET name = %s WHERE longitude = %s"

    start_cpu = time.process_time()

    for new_name, value in updates:
        try:
            cursor.execute(sql_template, (new_name, value))
            conn.commit()
            updates_count += 1
        except pymysql.MySQLError as e:
            print(f"Process {process_id} error: {e}")
            conn.rollback()

    end_cpu = time.process_time()
    execution_time = end_cpu - start_cpu
    result_queue.put(execution_time)

    cursor.close()
    conn.close()
    print(f"Process {process_id} completed {updates_count} updates.")


def run_experiment(index_type, run_number):
    print(f"\n[Run {run_number}/10] Running experiment with {index_type.upper()} index (MySQL)...")

    updates = load_csv_data(CSV_FILE, index_type=index_type, run_number=run_number)
    # 10 processes * 100 updates each
    sampled_updates = pick(updates, 1000, run_number)
    updates_split = [sampled_updates[i * 100:(i + 1) * 100] for i in range(10)]

    result_queue = multiprocessing.Queue()
    processes = []

    start_real_time = time.time()

    for i in range(10):
        p = multiprocessing.Process(
            target=update_task,
            args=(i + 1, index_type, updates_split[i], result_queue)
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    end_real_time = time.time()
    response_time = end_real_time - start_real_time
    execution_time = sum(result_queue.get() for _ in range(10))

    print("Experiment completed.")
    print(f"  Response Time (Real):   {response_time:.4f} seconds")
    print(f"  Execution Time (CPU):   {execution_time:.4f} seconds")

    # Append timing to CSV (label: scan / nonclustered / clustered)
    with RESULTS_CSV.open("a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "mysql",
            os.environ.get("TAG", "") + index_type,
            run_number,
            f"{execution_time:.6f}",
            f"{response_time:.6f}",
        ])


if __name__ == "__main__":
    init_results_csv()
    for i in range(1, 11):
        run_experiment(index_type="scan", run_number=i)
    for i in range(1, 11):
        run_experiment(index_type="clustered", run_number=i)
