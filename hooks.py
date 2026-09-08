"""Install transport dependencies into the framework runtime."""
import subprocess
import sys


def install(**kwargs):
    subprocess.run([sys.executable, "-m", "pip", "install", 'boto3==1.43.36'], check=True)
