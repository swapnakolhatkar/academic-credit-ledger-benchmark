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

def run_single_transaction():
    """
    Executes a single student credit transaction with retry logic.
    Returns a dictionary of local metrics for this transaction attempt.
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
    credit_data = {
        'transaction_id': fake.uuid4(),
        'apaar_id': f"APAAR-{random.randint(100000000000, 999999999999)}",
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'course_code': f"CS-{random.randint(100, 999)}",
        'credits_earned': random.choice([3, 4, 2]),
        'grade_points': random.choice([8, 9, 10, 7]),
        'institution_id': f"INST-{random.randint(10, 99)}",
        'state_code': random.choice(state_codes)
    }

    # Open a thread-specific connection
    try:
        conn = psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        metrics['connection_errors'] += 1
        return metrics

    while attempt < max_retries:
        attempt += 1
        try:
            with conn.cursor() as cursor:
                # 1. UPSERT student profile
                cursor.execute(
                    """
                    UPSERT INTO students (apaar_id, first_name, last_name, state_code, institution_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    """,
                    (credit_data['apaar_id'], credit_data['first_name'], credit_data['last_name'], 
                     credit_data['state_code'], credit_data['institution_id'])
                )
                
                # 2. Insert credit record into ABC ledger
                cursor.execute(
                    """
                    INSERT INTO abc_credits (transaction_id, apaar_id, course_code, credits_earned, grade_points, state_code, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (credit_data['transaction_id'], credit_data['apaar_id'], credit_data['course_code'],
                     credit_data['credits_earned'], credit_data['grade_points'], credit_data['state_code'])
                )
            
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
            
            # Exponential backoff with random jitter
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

def run_benchmark(total_transactions=200, concurrent_threads=50):
    """
    Runs the benchmark concurrently using ThreadPoolExecutor.
    """
    print(f"\nStarting benchmark: {total_transactions} total transactions with {concurrent_threads} concurrent threads...")
    
    global_metrics = {
        'success_count': 0,
        'serialization_retry_count': 0,
        'connection_error_count': 0,
        'max_retry_exhausted': 0
    }

    start_time = time.time()

    # Use ThreadPoolExecutor to manage concurrency
    with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
        # Submit all tasks to the pool
        futures = [executor.submit(run_single_transaction) for _ in range(total_transactions)]
        
        # Collect results as they complete
        for future in as_completed(futures):
            res = future.result()
            global_metrics['success_count'] += res['success']
            global_metrics['serialization_retry_count'] += res['serialization_retries']
            global_metrics['connection_error_count'] += res['connection_errors']
            global_metrics['max_retry_exhausted'] += res['max_retry_exhausted']

    duration = time.time() - start_time
    
    # Print Summary
    print("\n--- Concurrency Benchmark Summary ---")
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
    
    # Test with different concurrency thread levels (e.g., 10, 50, 100, 200)
    for threads in [10, 50, 100]:
        run_benchmark(total_transactions=300, concurrent_threads=threads)
        time.sleep(1) # Brief pause between test runs