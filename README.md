# TinyJit
A Just-In-Time compiler for Python using LLVM.

This project was developed as part of my bachelor's thesis in Informatics. For a detailed exploration of the concepts and methodologies behind this project, you can find the full thesis paper [here](Thesis.pdf).

*DISCLAIMER* This is not a finished project, it does not support all the Python instructions and data structures.

## Example usage

Just import the library and add the decorator before any function that you want to compile. Something like:

```
from tinyjit import tinyjit

@tinyjit
def function_to_compile():
```

## The power of TinyJit

TinyJit can execute code much faster than the regular Python interpreter and on big, time-consuming cases, it runs faster than popular compilers, e.g. Cython, PyPy, Numba.

```
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
```

For the above code, that does absolutely nothing, the execution times are:

| Number | Cython | PyPy | Numba | TinyJit |
| --- | --- | --- | --- | --- |
| 1000 | < $1e^{-12}$ s | 0.001 s | 0.14 s | 0.016 s |
| -1000 | < $1e^{-12}$ s | < $1e^{-12}$ s | 0.15 s | 0.015 s |
| 1000000 | 0.025 s | 0.002s | 0.15 s | 0.016 s |
| -1000000 | 0.027 s | 0.002s | 015 s | 0.014 s |
| 10000000 | 0.246 s | 0.008 s | 0.15 s | 0.018 s |
| -10000000 | 0.245 s | 0.009 s | 0.15 s | 0.015 s |
| 1000000000 | 24.4 s | 0.76 s | 0.15 s | 0.26 s |
| -1000000000 | 24.04 s | 0.73 s | 0.16 s | 0.014 s |

