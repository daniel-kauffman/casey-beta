import contextlib
import resource


class MemoryManager(object):

    @contextlib.contextmanager
    def limit(limit, type=resource.RLIMIT_AS):
        soft_limit, hard_limit = resource.getrlimit(type)
        resource.setrlimit(type, (limit, hard_limit)) # set soft limit
        try:
            yield
        finally:
            resource.setrlimit(type, (soft_limit, hard_limit)) # restore

    with limit(1 << 30): # 1GB 
        # do the thing that might try to consume all memory
