import llvmlite.binding as binding
import pathlib
from ctypes import CFUNCTYPE, ArgumentError, c_int8, POINTER

import llvmlite.ir


class JitEngine():
    def __init__(self):
        self.modules = {}
        self.engines = {}
        self.pass_manager = None
        self.engine = None

        binding.initialize()
        binding.initialize_native_target()
        binding.initialize_native_asmprinter()

    def create_execution_engine(self):
        # target machine that represents the host
        target_machine = binding.Target.from_default_triple().create_target_machine()
        # execution engine with an empty backing module
        backing_module = binding.parse_assembly("")
        engine = binding.create_mcjit_compiler(backing_module, target_machine)

        self.pass_manager = binding.ModulePassManager()
        binding.PassManagerBuilder().populate(self.pass_manager)

        return engine

    def compile_ir(self, ir, optimization_lvl=None):
        # try to create llvm module from ir
        try:
            module = binding.parse_assembly(ir)
            if optimization_lvl:
                if optimization_lvl is True:
                    optimization_lvl = 3
                self.pass_manager.opt_level = optimization_lvl
                self.pass_manager.run(module)
        except RuntimeError as e:
            print(ir)
            raise e

        module.verify()

        # add module and make sure it s ready for exec
        self.engine.add_module(module)
        self.engine.finalize_object()
        self.engine.run_static_constructors()

        return module

    def compile(self, generator, optimization_lvl=True, entry_point="__main__", cnt=0):
        module_file = generator.python_mod.__file__
        module_path = pathlib.Path(module_file)
        module_path_base = module_path.parent
        module_filename = module_path.parts[-1]
        jit_module_filename = f"{module_filename}.jit"
        jit_module_path = pathlib.Path(module_path_base, jit_module_filename)
        ###

        self.engine = self.engines.get(generator.python_mod_name, None)
        if self.engine is None:
            self.engine = self.create_execution_engine()

        compile_jit = False

        # for multiple functions within a file

        if cnt:
            compile_jit = True

        if jit_module_path.exists():
            if jit_module_path.stat().st_mtime < module_path.stat().st_mtime:
                compile_jit = True
        else:
            compile_jit = True

        if compile_jit:
            module = self.compile_ir(str(generator.module), optimization_lvl)
            with open(f"{module_file}.jit", "wb") as f:
                f.write(module.as_bitcode())
        else:
            # is already compiled => load
            with open(f"{module_file}.jit", "rb") as f:
                module_bitcode = f.read()
            module = binding.parse_bitcode(module_bitcode)
            module.verify()
            self.engine.add_module(module)
            self.engine.finalize_object()
            self.engine.run_static_constructors()

        self.modules[generator.python_mod_name] = module

        arg_types = [arg.to_ctype() for arg in generator.arg_types]
        func = generator.module.globals[entry_point]
        if isinstance(func.return_type, llvmlite.ir.Type):
            ctype = func.return_type
        else:
            if func.return_type == str:
                ctype = POINTER(c_int8 * func.type.pointee.return_type.count)
            else:
                ctype = func.return_type.to_ctype()

        cfunc_type = CFUNCTYPE(ctype, *arg_types)

        def get_cfunc(*a, **ka):
            func_ptr = self.engine.get_function_address(entry_point)
            cfunc = cfunc_type(func_ptr)
            try:
                return cfunc(*a, **ka)
            except ArgumentError:
                raise Exception(f"Couldn't return C function for {func_ptr}")

        get_cfunc.restype = ctype

        return get_cfunc


jit_engine = JitEngine()

