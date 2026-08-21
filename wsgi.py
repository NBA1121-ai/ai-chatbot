import sys
import os

sys.setrecursionlimit(3000)

path = '/home/Beka2121/ai-chatbot'
if path not in sys.path:
    sys.path.append(path)

# Set GEMINI_API_KEY via PythonAnywhere environment variables
os.chdir(path)

from server import app as application
