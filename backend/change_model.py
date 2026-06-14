import sys
import os

# Ensure we're in the right directory to import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core_engine.database import SessionLocal
from core_engine.models import SystemSetting

def change_model(new_model="gemma4:e4b"):
    db = SessionLocal()
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == 'active_model').first()
        if setting:
            print(f"Old model was: {setting.value}")
            setting.value = new_model
        else:
            print("No active_model setting found. Creating one.")
            setting = SystemSetting(key='active_model', value=new_model)
            db.add(setting)
        
        # Setează și contextul mai mic pentru a preveni timeout
        ctx_setting = db.query(SystemSetting).filter(SystemSetting.key == 'chat_ctx').first()
        if ctx_setting:
            ctx_setting.value = '8192'
        else:
            db.add(SystemSetting(key='chat_ctx', value='8192'))

        db.commit()
        print(f"Success! Model updated to {new_model} with context 8192.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    change_model()
