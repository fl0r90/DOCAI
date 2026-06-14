
import os
import sys
# Adaugam calea corecta pentru importuri
sys.path.append(os.getcwd())
from backend.core_engine.core.security import create_access_token

token = create_access_token(data={"sub": "admin", "role": "ADMIN"})
print(token)
