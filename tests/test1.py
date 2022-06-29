from tinyjit import tinyjit
import tinyjit.jit_types as t
import time
import tracemalloc


tracemalloc.start()
start_time = time.time()


@tinyjit
def more_complex(number: t.i64):
    b = 0
    if number > 0:
        while number:
            b *= number
            number -= 1
    else:
        while number:
            b = b << 0
            number += 1
    return b


more_complex(3)

print(f"Exec time: {(time.time() - start_time)} seconds")
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage is {current / 10**6}MB; Peak was {peak / 10**6}MB")
tracemalloc.stop()
