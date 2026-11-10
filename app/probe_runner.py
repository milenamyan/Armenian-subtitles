"""Child-process limits before exec; never imports the app or logs its arguments."""
import os
import sys

if os.name=='posix':
    import resource
    memory=int(os.getenv('HAYSUB_FFPROBE_MEMORY_MB','512'))*1024**2
    timeout=int(os.getenv('HAYSUB_FFPROBE_TIMEOUT_SECONDS','120'))
    resource.setrlimit(resource.RLIMIT_AS,(memory,memory))
    resource.setrlimit(resource.RLIMIT_CPU,(timeout,timeout+1))
    resource.setrlimit(resource.RLIMIT_FSIZE,(2*1024**2,2*1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
os.execvp(sys.argv[1],sys.argv[1:])
