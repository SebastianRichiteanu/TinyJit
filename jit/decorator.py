from .engine import jit_engine
from .generator import jit_generator
from .jit_types import JitType

cnt = 0

def tinyjit(function):
    def wrapper(*a, **kwargs):
        aa = []
        for argument in a:
            if isinstance(argument, JitType):
                aa.append(argument.from_jtype(argument))
            else:
                aa.append(argument)

        try:
            return function._jit(*aa, **kwargs)
        except AttributeError:
            pass

        try:
            jit_generator.generate_all(function, aa)
        except Exception as e:
            raise e

        global cnt
        jitted_function = jit_engine.compile(jit_generator, entry_point=function.__name__, cnt=cnt)
        cnt += 1
        function._jit = jitted_function
        result = jitted_function(*aa, **kwargs)

        if hasattr(result, "contents"):
            return result.contents
        return result

    wrapper._wrapper = function
    return wrapper


