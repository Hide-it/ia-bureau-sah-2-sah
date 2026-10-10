import os, sys, json, time, datetime
from pathlib import Path

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

try:
    import readline
except ImportError:
    pass  
##ici tu prend tout squil y a sur nvidia nim et apres tu suis le guide ptit trdbl##
API_KEY_FILE = Path.home() / ".nvidia_nim_key"
BASE_URL     = "https://integrate.api.nvidia.com/v1/chat/completions"   
MODEL        = "deepseek-ai/deepseek-v4-flash-0731"

R   = "\033[0m";  B  = "\033[1m";  DIM = "\033[2m"
CY  = "\033[96m"; GR = "\033[92m"; YL  = "\033[93m"; RD = "\033[91m"

SYSTEM_PROMPT = (
        ""         ##met ton prompt z3ma cmt l'ia se comporte##
)

def banner():
    print(f"""
{CY}{B}
      ::::::::  :::::::::: ::::::::::          ::::::::::: :::::::::::
    :+:    :+: :+:        :+:                     :+:         :+:
   +:+        +:+        +:+                     +:+         +:+
  +#++:++#+  +#++:++#   +#++:++#                +#+         +#+
        +#+ +#+        +#+                     +#+         +#+
#+#    #+# #+#        #+#                     #+#         #+#
########  ########## ##########          ###########     ###{R}
{YL}  powered by DeepSeek V4 Pro · SEEK & SEE · SEEK FOR THE TRUTH{R}
""")

def get_api_key():
    key = os.environ.get("NVIDIA_API_KEY", "")
    if key: return key
    if API_KEY_FILE.exists():
        key = API_KEY_FILE.read_text().strip()
        if key: return key
    print(f"{YL}pas d'api{R}")
    print(f"   save dans : {API_KEY_FILE}\n")
    key = input(f"{CY}   Colle ta clé nvapi : {R}").strip()
    if key:
        API_KEY_FILE.write_text(key)
        print(f"{GR}   save.\n{R}")
    return key

def read_file(path_str):
    path = Path(path_str.strip().strip("'\""))
    if not path.exists():
        return None, f"Fichier introuvable : {path}"
    if path.stat().st_size > 20 * 1024 * 1024:
        return None, "max 20mo"
    try:
        return path.read_text(encoding="utf-8", errors="replace"), None
    except Exception as e:
        return None, str(e)

def write_file(path_str, content):
    path = Path(path_str.strip().strip("'\""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path

def extract_and_save_files(ai_response):
    import re

    pattern = r"```(?:filename:|file:)([^\n]+)\n([\s\S]*?)```"
    matches = re.findall(pattern, ai_response)
    saved = []
    for fname, content in matches:
        fname = fname.strip()
        try:
            p = write_file(fname, content)
            saved.append(str(p))
        except Exception as e:
            print(f"{RD}  erreur writing {fname} : {e}{R}")
    return saved


def call_api_stream(api_key, messages):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.7,
        "stream": True,
    }
    return requests.post(BASE_URL, headers=headers, json=payload, stream=True, timeout=60)

def stream_response(response):
    full = ""
    for line in response.iter_lines():
        if not line: continue
        line = line.decode("utf-8")
        if line.startswith("data: "):
            data = line[6:]
            if data == "[DONE]": break
            try:
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"].get("content", "")
                if delta:
                    print(delta, end="", flush=True)
                    full += delta
            except Exception:
                pass
    return full

##help fait pas l'ia sah 2 sah##
def print_help():
    print(f"""
{B}Commandes :{R}
  {CY}/file <chemin>{R}         Lire et joindre un fichier
  {CY}/files <c1> <c2>{R}      Joindre plusieurs fichiers
  {CY}/write <chemin>{R}        Créer/écraser un fichier (contenu saisi ensuite)
  {CY}/edit <chemin>{R}         Afficher le fichier puis demander des modifs à l'IA
  {CY}/clear{R}                 Réinitialiser la conversation
  {CY}/save{R}                  Sauvegarder la conversation en .txt
  {CY}/help{R}                  Cette aide
  {CY}/quit{R}                  Quitter


""")

def save_conversation(history):
    fname = f"seek_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    lines = [f"[{m['role'].upper()}]\n{m['content']}\n\n{'─'*60}\n"
             for m in history if m["role"] != "system"]
    Path(fname).write_text("\n".join(lines), encoding="utf-8")
    print(f"{GR}  Sauvegardé : {fname}{R}")

def main():
    if sys.platform == "win32":
        os.system("color")
        try:
            sys.stdin  = open("CONIN$",  "r")
            sys.stdout = open("CONOUT$", "w")
            sys.stderr = open("CONOUT$", "w")
        except Exception:
            pass

    banner()
    api_key = get_api_key()
    if not api_key:
        print(f"{RD}pas d'api.{R}")
        input("Appui sur Entrer pour fermer")
        sys.exit(1)


    def fresh_history():
        return [{"role": "system", "content": SYSTEM_PROMPT}]

    history = fresh_history()
    pending_files = []



    while True:
        try:
            indicator = f"{YL}[+{len(pending_files)} fichier(s)] {R}" if pending_files else ""
            user_input = input(f"\n{GR}{B}Hide it›{R} {indicator}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}Aller salem{R}")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower().split()[0]

            if cmd in ("/quit", "/exit", "/q"):
                print(f"{DIM}Jme casse{R}"); break

            elif cmd == "/help":
                print_help(); continue

            elif cmd == "/clear":
                history = fresh_history()
                pending_files = []
                print(f"{GR}  Conversation reset{R}"); continue

            elif cmd == "/save":
                save_conversation(history); continue

            elif cmd in ("/file", "/files"):
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print(f"{YL}  Usage : /file <chemin>{R}"); continue
                for p in parts[1].split():
                    content, err = read_file(p)
                    name = Path(p.strip()).name
                    if err:
                        print(f"{RD}  {name} : {err}{R}")
                    else:
                        pending_files.append((name, content))
                        print(f"{GR}  {name} charger ({len(content):,} car.){R}")
                continue

            elif cmd == "/write":
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print(f"{YL}  Usage : /write <chemin>{R}"); continue
                fpath = parts[1].strip()
                print(f"{DIM}  fini la ligne avec EOF :{R}")
                lines = []
                while True:
                    try:
                        line = input()
                        if line == "EOF": break
                        lines.append(line)
                    except (KeyboardInterrupt, EOFError):
                        break
                content = "\n".join(lines)
                try:
                    p = write_file(fpath, content)
                    print(f"{GR}  Fichier crer : {p}{R}")
                except Exception as e:
                    print(f"{RD}  Erreur : {e}{R}")
                continue

            elif cmd == "/edit":
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print(f"{YL}  Usage : /edit <chemin>{R}"); continue
                fpath = parts[1].strip()
                content, err = read_file(fpath)
                if err:
                    print(f"{RD}  {err}{R}"); continue
                name = Path(fpath).name
                pending_files.append((name, content))
                print(f"{GR}  {name} pres a modifier{R}")
                continue

            else:
                print(f"{YL}  existe pas : {cmd}{R}"); continue

        content = user_input
        if pending_files:
            blocks = [f"### Fichier : {n}\n```\n{fc[:15000]}{'...(tronquer)' if len(fc)>15000 else ''}\n```"
                      for n, fc in pending_files]
            content += "\n\nfichier apporter\n\n" + "\n\n".join(blocks)
            pending_files = []

        history.append({"role": "user", "content": content})
        print(f"\n{CY}{B}SEEK & SEE ›{R}")

        try:
            resp = None
            for attempt in range(5):
                resp = call_api_stream(api_key, history)
                if resp.status_code != 429: break
                wait = 10 * (attempt + 1)
                print(f"{YL}  Rate limit — attente {wait}s...{R}")
                time.sleep(wait)

            if resp.status_code != 200:
                try:
                    msg = resp.json().get("detail") or resp.json().get("message") or resp.text
                except Exception:
                    msg = resp.text
                print(f"{RD}  Erreur {resp.status_code} : {msg}{R}")
                history.pop()
                continue

            full = stream_response(resp)
            print()


            saved = extract_and_save_files(full)
            for s in saved:
                print(f"{GR}  Fichier save {s}{R}")

            history.append({"role": "assistant", "content": full})

        except requests.exceptions.ConnectionError:
            print(f"{RD}  pas de co.{R}")
            history.pop()
        except Exception as e:
            print(f"{RD}  Erreur  {e}{R}")
            history.pop()

if __name__ == "__main__":
    main()
