import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mcp.api.client import search_category

result = search_category(gender=0, keyword="总裁")
print(result)