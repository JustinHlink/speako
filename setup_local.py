"""One-step local setup for Speako. setup.bat (Windows) and setup.sh (macOS, Linux) run this file.

It is safe to run again: every step checks what is already done.
"""
import getpass
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV, EXAMPLE = ROOT / '.env', ROOT / '.env.example'
DEMO_PASSWORD = os.environ.get('SPEAKO_DEMO_PASSWORD') or 'SpeakoDemo2026!'
START = 'start.bat (double-click it)' if os.name == 'nt' else 'bash start.sh'
KEYS = [('ANTHROPIC_API_KEY', 'Claude', 'sk-ant-'), ('GROQ_API_KEY', 'Groq', 'gsk_')]


def step(number, text):
    print(f'\n[{number}/6] {text}', flush=True)


def stop(text):
    print(f'\nSetup stopped: {text}\nFix this, then run the setup again.', flush=True)
    sys.exit(1)


def run(*args, env=None):
    result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env)
    if result.returncode != 0:
        stop(f'this command failed: python {" ".join(args)}')


def read_env():
    values = {}
    for line in ENV.read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()
    return values


def write_private(path, text):
    """Write a file that only the current user can read (macOS, Linux). Windows ignores the mode."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(text)
    if os.name != 'nt':
        os.chmod(path, 0o600)  # Also tightens an older .env that was created readable by others.


def set_env_value(key, value):
    lines = ENV.read_text(encoding='utf-8-sig').splitlines()
    for i, line in enumerate(lines):
        if line.split('=', 1)[0].strip() == key:
            lines[i] = f'{key}={value}'
            break
    else:
        lines.append(f'{key}={value}')
    write_private(ENV, '\n'.join(lines) + '\n')


def prepare_env():
    if not ENV.exists():
        write_private(ENV, EXAMPLE.read_text(encoding='utf-8'))
        print('Created .env from .env.example.')
    elif os.name != 'nt':
        os.chmod(ENV, 0o600)
    # An older .env gets any setting it is missing, with the example's value. Existing values stay.
    current = read_env()
    added = []
    for line in EXAMPLE.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            if key.strip() not in current:
                set_env_value(key.strip(), value.strip())
                added.append(key.strip())
    if added:
        print('Added missing settings to .env:', ', '.join(added))
    for setting, name, prefix in KEYS:
        if read_env().get(setting):
            print(f'The {name} API key is already in .env.')
            continue
        print(f'Speako needs a {name} API key. Your team lead gives it to you privately.')
        print('Typing is hidden. Paste the key, then press Enter.')
        key = getpass.getpass(f'{name} API key: ').strip()
        if not key.startswith(prefix):
            stop(f'that does not look like a {name} API key (it must start with {prefix}).')
        set_env_value(setting, key)
        print('Saved the key in .env. Git ignores this file, so the key never goes to GitHub.')


def check_keys():
    import urllib.error
    import urllib.request
    import anthropic
    env = read_env()
    try:
        anthropic.Anthropic(api_key=env.get('ANTHROPIC_API_KEY', ''), timeout=20.0, max_retries=1).models.list(limit=1)
        print('The Claude API key works.')
    except anthropic.AuthenticationError:
        stop('Claude rejected the API key. Remove the ANTHROPIC_API_KEY value from .env and run the setup again.')
    except Exception as exc:  # A network problem must not block the rest of the setup.
        print(f'Could not check the Claude key now ({type(exc).__name__}). Setup continues; check your internet connection.')
    request = urllib.request.Request('https://api.groq.com/openai/v1/models', headers={
        'Authorization': f"Bearer {env.get('GROQ_API_KEY', '')}", 'User-Agent': 'speako'})
    try:
        urllib.request.urlopen(request, timeout=20).read()
        print('The Groq API key works.')
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            stop('Groq rejected the API key. Remove the GROQ_API_KEY value from .env and run the setup again.')
        print(f'Could not check the Groq key now (HTTP {exc.code}). Setup continues.')
    except Exception as exc:
        print(f'Could not check the Groq key now ({type(exc).__name__}). Setup continues; check your internet connection.')


def download_speech_model():
    model = read_env().get('WHISPER_MODEL') or 'small.en'
    os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
    print(f'Getting the speech model {model}. The first time, this downloads about 464 MB.')
    try:
        from faster_whisper import WhisperModel
        WhisperModel(model, device='cpu', compute_type=read_env().get('WHISPER_COMPUTE_TYPE') or 'int8')
    except Exception as exc:
        stop(f'the speech model could not be downloaded or loaded ({type(exc).__name__}). Check your internet connection.')
    print('The speech model is ready.')


def main():
    if not (3, 10) <= sys.version_info[:2] <= (3, 13):
        stop(f'Speako needs Python 3.10 to 3.13. This is Python {sys.version.split()[0]}.')
    os.chdir(ROOT)
    step(1, 'Install the Python packages (the first time takes a few minutes)')
    run('-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '-r', 'requirements.txt')
    print('The packages are installed.')
    step(2, 'Create .env and add the API keys')
    prepare_env()
    step(3, 'Check the API keys')
    check_keys()
    step(4, 'Create the database and the lessons')
    run('manage.py', 'migrate', '--noinput')
    step(5, 'Create the demo accounts')
    run('manage.py', 'seed_demo_users', env={**os.environ, 'SPEAKO_DEMO_PASSWORD': DEMO_PASSWORD})
    step(6, 'Download the backup speech-to-text model')
    download_speech_model()
    print('\nSetup is complete.')
    print(f'Start Speako with: {START}')
    print('Then open http://127.0.0.1:8001/ in Chrome or Edge.')
    print(f'Sign in as learner1, learner2 or reviewer1. Password: {DEMO_PASSWORD}')


if __name__ == '__main__':
    main()
