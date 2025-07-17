import time
import tracemalloc

def profile_algorithm(algorithm_fn, *args, **kwargs):
    # Start tracking time and memory
    tracemalloc.start()
    start_time = time.time()

    # Run the algorithm
    result = algorithm_fn(*args, **kwargs)

    # Stop tracking
    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Output results
    print(f"Execution time: {end_time - start_time:.4f} seconds")
    print(f"Current memory usage: {current / 1024:.2f} KB")
    print(f"Peak memory usage: {peak / 1024:.2f} KB")
    
    return result
