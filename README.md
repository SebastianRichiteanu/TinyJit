# TinyJit ⚙️🐍  
*A Just-In-Time Compiler for Python using LLVM*

TinyJit is a lightweight JIT compiler for Python that leverages LLVM to accelerate Python functions at runtime. It was developed as part of my Bachelor’s thesis in Computer Science at the University of Bucharest. You can explore the full thesis [here](Thesis.pdf) for in-depth explanations, architecture, and performance benchmarks.

> ⚠️ **Note**: TinyJit is a prototype and does not yet support all Python instructions or data structures.

---

## 🎯 Key Features

- 🔧 **Decorator-Based JIT Compilation**  
  Compile only the functions you want with a simple `@tinyjit` decorator.

- 🧠 **LLVM Integration**  
  Uses LLVM’s IR and execution engine via [llvmlite](https://llvmlite.readthedocs.io/) for efficient low-level code generation.

- 🚀 **Performance Boost**  
  Shows major speedups in large computational loops, often outperforming tools like Cython, Numba, and PyPy in specific cases.

- 🧪 **Testable & Extensible**  
  Modular structure with debug output, AST generation, and a suite of performance experiments.

---

## 🔍 Background

Python’s interpreted nature makes it easy to use but slow to execute. TinyJit bridges that gap by compiling individual functions at runtime, allowing developers to optimize only performance-critical code while leaving the rest of the code untouched.

Unlike general-purpose compilers like PyPy or Cython, TinyJit is:
- ✅ Minimalistic and targeted
- ✅ Customizable through Python decorators
- ✅ Focused on understanding compiler construction (great for learning!)

📘 *See the [Thesis.pdf](Thesis.pdf) for implementation details, LLVM IR samples, and test results.*

---

## 📦 Installation

```bash
pip install llvmlite
```

Clone the repo:

```bash
git clone https://github.com/SebastianRichiteanu/TinyJit.git
cd TinyJit
```

---

## 🧪 Usage Example

Just decorate any function you want to compile:

```python
from tinyjit import tinyjit

@tinyjit
def fib(n):
    a = 0
    b = 1
    while b < n:
        a, b = b, a + b
    return a
```

Or, try a more complex example:

```python
from tinyjit import tinyjit, t

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


Run your script as usual — TinyJit will JIT compile only the decorated function.

---

## ⚡ Performance Comparison

The following table shows execution times (in seconds) for the `more_complex` function:

| Number       | Cython | PyPy  | Numba | TinyJit |
|--------------|--------|-------|--------|---------|
| 1000         | ~0     | 0.001 | 0.14   | 0.016   |
| -1000        | ~0     | ~0    | 0.15   | 0.015   |
| 1,000,000    | 0.025  | 0.002 | 0.15   | 0.016   |
| -1,000,000   | 0.027  | 0.002 | 0.15   | 0.014   |
| 10,000,000   | 0.246  | 0.008 | 0.15   | 0.018   |
| -10,000,000  | 0.245  | 0.009 | 0.15   | 0.015   |
| 1,000,000,000| 24.4   | 0.76  | 0.15   | 0.26    |
| -1,000,000,000| 24.04 | 0.73  | 0.16   | 0.014   |

---

## 🧱 Architecture Overview

- `decorator.py` – wraps Python functions and triggers JIT compilation
- `generator.py` – converts AST into LLVM IR
- `engine.py` – compiles and executes the LLVM code
- `jit_types.py` – defines supported types and handles type conversions
- `standard_func.py` – built-in functions like `print`, `range`
- `debug/` – optional output for generated IR and AST (when debug is enabled)

---

## 🚧 Limitations

- Does not support all Python constructs (e.g., complex classes, dynamic types)
- Only works on explicitly typed function arguments (use `t.i64`, `t.float`, etc.)
- No exception handling
- Memory usage is higher due to variable duplication when type casting

---

## 🧠 Behind the Compiler

TinyJit processes functions in 4 main stages:
1. **Source Extraction**: Using Python's `inspect` module
2. **AST Parsing**: Converts function source into an abstract syntax tree
3. **IR Generation**: Maps AST nodes to LLVM IR using `llvmlite`
4. **Execution**: Runs the compiled IR with LLVM's JIT engine

---

## 📈 Benchmarking Setup

- **Platform**: Linux / macOS / Windows  
- **Compiler**: LLVM via `llvmlite`  
- **Profiler**: `time`, `tracemalloc` for memory comparison  
- **Reference Compilers**: Cython, PyPy, Numba  

---

## 🔗 Links

- 📚 [Thesis.pdf](Thesis.pdf)
- 🐍 [Python AST Docs](https://docs.python.org/3/library/ast.html)
- 📘 [LLVM LangRef](https://llvm.org/docs/LangRef.html)
- ⚙️ [llvmlite Docs](https://llvmlite.readthedocs.io/)
