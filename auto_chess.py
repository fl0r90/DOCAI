import ollama, subprocess, json, time, sys

def run_cmd(cmd):
    print(f'-> Executing: {cmd}')
    if 'sudo' in cmd:
        cmd = f'echo 1 | sudo -S {cmd.replace("sudo ", "")}'
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return f'OUT: {res.stdout}\nERR: {res.stderr}'
    except Exception as e:
        return str(e)

def start():
    client = ollama.Client(host='http://localhost:11434')
    msgs = [
        {'role': 'system', 'content': 'Esti un programator AUTONOM. Sarcina: creeaza un joc de sah pe portul 5005 (Flask + python-chess + frontend). Instaleaza tot, scrie tot, porneste serverul. Foloseste run_cmd.'},
        {'role': 'user', 'content': 'START'}
    ]

    for i in range(40):
        try:
            print(f'[*] Pasul {i+1}...')
            resp = client.chat(
                model='qwen2.5-coder:7b',
                messages=msgs,
                tools=[{
                    'type': 'function',
                    'function': {
                        'name': 'run_cmd',
                        'parameters': {'type': 'object', 'properties': {'command': {'type': 'string'}}, 'required': ['command']}
                    }
                }]
            )
            
            m = resp['message']
            msgs.append(m)
            
            if m.get('tool_calls'):
                for t in m['tool_calls']:
                    out = run_cmd(t['function']['arguments']['command'])
                    msgs.append({'role': 'tool', 'content': out})
            elif 'run_cmd' in (m.get('content') or ''):
                # Fallback for text JSON
                try:
                    c = m['content']
                    if '```json' in c: c = c.split('```json')[1].split('```')[0]
                    data = json.loads(c.strip())
                    out = run_cmd(data['arguments']['command'])
                    msgs.append({'role': 'tool', 'content': out})
                except:
                    print('[!] Failed to parse JSON content')
            
            if i > 10 and '5005' in (m.get('content') or '').lower():
                print('[DONE] Agent reports completion.')
                break
            
            time.sleep(1)
        except Exception as e:
            print(f'Loop Error: {e}')
            break

if __name__ == '__main__':
    start()
