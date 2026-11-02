import time
import random
import psycopg2
from psycopg2 import OperationalError, errorcodes
from faker import Faker
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize Faker for synthetic data generation
fake = Faker('en_IN')

# Database connection configuration
DB_CONFIG = {
    "dbname": "defaultdb",
    "user": "root",
    "password": "",
    "host": "localhost",
    "port": "26257"
}

def setup_database():
    """Initializes the educational schema tables once before benchmarking."""
    conn = psycopg2.connect(**DB_CONFIG)
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                apaar_id STRING PRIMARY KEY,
                first_name STRING,
                last_name STRING,
                state_code STRING,
                institution_id STRING,
                created_at TIMESTAMPTZ
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS abc_credits (
                transaction_id STRING PRIMARY KEY,
                apaar_id STRING REFERENCES students(apaar_id),
                course_code STRING,
                credits_earned INT,
                grade_points INT,
                state_code STRING,
                timestamp TIMESTAMPTZ
            );
        """)
    conn.commit()
    conn.close()
    print("Database tables verified/created successfully.")

def run_workload_b_transaction():
    """
    Simulates Workload B (Peak Exam Season / Write-Heavy Profile):
    - 70% probability: Heavy write/update (Upsert student + Insert new credit ledger entry).
    - 30% probability: Read-heavy credential verification query.
    Returns metrics dictionary.
    """
    metrics = {
        'success': 0,
        'serialization_retries': 0,
        'connection_errors': 0,
        'max_retry_exhausted': 0
    }
    
    max_retries = 5
    attempt = 0
    
    state_codes = ['MH', 'KA', 'DL', 'TN', 'UP', 'GJ']
    selected_state = random.choice(state_codes)
    
    # Determine operation type based on Workload B distribution (70% Write / 30% Read)
    is_write_operation = random.random() < 0.70

    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        metrics['connection_errors'] += 1
        return metrics

    while attempt < max_retries:
        attempt += 1
        try:
            with conn.cursor() as cursor:
                if is_write_operation:
                    # Write-Heavy Transaction: Exam Result Declaration / Grade Update
                    apaar_id = f"APAAR-{random.randint(100000000000, 999999999999)}"
                    cursor.execute(
                        """
                        UPSERT INTO students (apaar_id, first_name, last_name, state_code, institution_id, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        """,
                        (apaar_id, fake.first_name(), fake.last_name(), selected_state, f"INST-{random.randint(10, 99)}")
                    )
                    cursor.execute(
                        """
                        INSERT INTO abc_credits (transaction_id, apaar_id, course_code, credits_earned, grade_points, state_code, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        """,
                        (fake.uuid4(), apaar_id, f"CS-{random.randint(100, 999)}", random.choice([3, 4, 2]), random.choice([8, 9, 10]), selected_state)
                    )
                else:
                    # Read-Heavy Transaction: Credential/Credit Verification by Employer/University
                    cursor.execute(
                        """
                        SELECT s.apaar_id, s.first_name, s.last_name, c.course_code, c.credits_earned, c.grade_points 
                        FROM students s 
                        LEFT JOIN abc_credits c ON s.apaar_id = c.apaar_id 
                        WHERE s.state_code = %s LIMIT 5
                        """,
                        (selected_state,)
                    )
                    cursor.fetchall()
            
            conn.commit()
            metrics['success'] = 1
            break

        except OperationalError as e:
            conn.rollback()
            err_code = getattr(e, 'pgcode', None)
            
            if err_code == errorcodes.SERIALIZATION_FAILURE:
                metrics['serialization_retries'] += 1
                if attempt == max_retries:
                    metrics['max_retry_exhausted'] += 1
            else:
                metrics['connection_errors'] += 1
                if attempt == max_retries:
                    break
            
            # Exponential backoff with jitter
            time.sleep((2 ** attempt) * 0.02 + random.uniform(0, 0.02))
            
        except Exception as e:
            conn.rollback()
            break
        finally:
            if attempt == max_retries or metrics['success'] == 1:
                try:
                    conn.close()
                except:
                    pass

    return metrics

def run_benchmark(total_transactions=500, concurrent_threads=200):
    """
    Runs Workload B concurrently using ThreadPoolExecutor up to high thread counts.
    """
    print(f"\nSimulating Workload B (70% Write / 30% Read): {total_transactions} transactions with {concurrent_threads} concurrent threads...")
    
    global_metrics = {
        'success_count': 0,
        'serialization_retry_count': 0,
        'connection_error_count': 0,
        'max_retry_exhausted': 0
    }

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
        futures = [executor.submit(run_workload_b_transaction) for _ in range(total_transactions)]
        
        for future in as_completed(futures):
            res = future.result()
            global_metrics['success_count'] += res['success']
            global_metrics['serialization_retry_count'] += res['serialization_retries']
            global_metrics['connection_error_count'] += res['connection_errors']
            global_metrics['max_retry_exhausted'] += res['max_retry_exhausted']

    duration = time.time() - start_time
    
    print("\n--- Workload B Benchmark Summary ---")
    print(f"Concurrent Threads Used       : {concurrent_threads}")
    print(f"Total Transactions Attempted  : {total_transactions}")
    print(f"Successful Transactions       : {global_metrics['success_count']}")
    print(f"Serialization Retries Handled : {global_metrics['serialization_retry_count']}")
    print(f"Connection Errors             : {global_metrics['connection_error_count']}")
    print(f"Max Retries Exhausted         : {global_metrics['max_retry_exhausted']}")
    print(f"Total Time Taken              : {duration:.2f} seconds")
    print(f"Calculated Throughput (TPS)   : {global_metrics['success_count'] / duration:.2f}")

if __name__ == "__main__":
    setup_database()
    
    # Scaling up to high concurrency tiers mirroring the research paper (100 and 200 threads)
    for threads in [100, 200]:
        run_benchmark(total_transactions=600, concurrent_threads=threads)
        time.sleep(1)