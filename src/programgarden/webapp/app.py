from flask import Flask, request, jsonify, render_template, send_from_directory
import threading
import json
import os
import ast
import datetime
from collections import deque, OrderedDict
import logging

from programgarden.client import Programgarden
import pprint

app = Flask(__name__, static_folder='static', template_folder='templates')

# Simple in-memory flag to show running state
running = {"is_running": False}

# Paths
BASE_DIR = os.path.dirname(__file__)
LAST_RUN_PATH = os.path.join(BASE_DIR, 'last_run_config.json')

# simple in-memory logs (most recent first)
LOG_MAX = 500
log_lock = threading.Lock()
logs = deque(maxlen=LOG_MAX)

# current running Programgarden instance (if any)
current_pg = None
current_pg_lock = threading.Lock()

# configure basic logging to stdout as well
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# reduce werkzeug access log verbosity
try:
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.WARNING)
except Exception:
    pass


def add_log(message: str, level: str = 'INFO'):
    ts = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    entry = f"{ts} [{level}] {message}"
    with log_lock:
        logs.append(entry)
    # also send to standard logging
    if level == 'ERROR':
        logging.error(message)
    elif level == 'WARN' or level == 'WARNING':
        logging.warning(message)
    else:
        logging.info(message)


def ensure_last_run_config():
    if not os.path.exists(LAST_RUN_PATH):
        default = OrderedDict([
            ("settings", OrderedDict([("name", "Example Condition")])),
            ("securities", OrderedDict()),
            ("strategies", []),
        ])
        with open(LAST_RUN_PATH, 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=2, sort_keys=False)


def make_ordered(obj):
    """Recursively convert mapping types to OrderedDict to preserve key order when dumping."""
    if isinstance(obj, dict):
        return OrderedDict((k, make_ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return [make_ordered(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(make_ordered(v) for v in obj)
    return obj


def run_trading_system(system_config: dict):
    """Mock runner for the trading system. Replace with an import from programgarden when running for real.

    This function simulates a long-running job and toggles the running flag.
    """
    try:
        running["is_running"] = True
        add_log('Run started')
        try:
            to_save = make_ordered(system_config)
            with open(LAST_RUN_PATH, 'w', encoding='utf-8') as f:
                json.dump(to_save, f, ensure_ascii=False, indent=2, sort_keys=False)
            add_log('Saved last_run_config.json')
        except Exception as e:
            add_log(f'Error saving last_run_config.json: {e}', level='ERROR')

        try:
            pg = Programgarden()
            add_log('Initialized Programgarden client')
            # store current pg so we can stop it from /stop
            with current_pg_lock:
                globals()['current_pg'] = pg

            # 실시간 주문 응답 콜백
            def _format_message(msg):
                try:
                    return json.dumps(msg, ensure_ascii=False, indent=2, default=str)
                except Exception:
                    return pprint.pformat(msg, indent=2)

            def _strip_key(msg, key='key'):
                try:
                    # dict-like objects
                    if isinstance(msg, dict):
                        return {k: v for k, v in msg.items() if k != key}
                    if hasattr(msg, 'items'):
                        return {k: v for k, v in msg.items() if k != key}
                    # try to convert to dict
                    try:
                        d = dict(msg)
                        return {k: v for k, v in d.items() if k != key}
                    except Exception:
                        return msg
                except Exception:
                    return msg

            pg.on_real_order_message(
                callback=lambda message: add_log(f"Real Order Message:\n{_format_message(_strip_key(message, 'response'))}")
            )
            pg.on_strategies_message(
                callback=lambda message: add_log(f"Strategies\n{_format_message(_strip_key(message, 'response'))}")
            )
            pg.run(system=system_config)
            add_log('Programgarden.run completed')
        except Exception as e:
            add_log(f'Error during Programgarden.run: {e}', level='ERROR')

        result = {"status": "ok", "message": "Executed run", "symbols": len(system_config.get('strategies', []))}
        return result
    finally:
        # clear current pg reference
        with current_pg_lock:
            globals()['current_pg'] = None
        running["is_running"] = False


@app.route('/')
def index():
    return render_template('editor.html')


@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)


@app.route('/run', methods=['POST'])
def run():
    if running["is_running"]:
        return jsonify({"status": "busy", "message": "Already running"}), 409
    # Accept either JSON (application/json) or plain text containing a Python literal
    text = request.get_data(as_text=True)
    if not text:
        return jsonify({"status": "error", "message": "Empty request body"}), 400

    data = None
    try:
        # prefer JSON parsing with OrderedDict to preserve key order
        data = json.loads(text, object_pairs_hook=OrderedDict)
        data = make_ordered(data)
    except Exception:
        try:
            parsed = ast.literal_eval(text)
            data = make_ordered(parsed)
        except Exception as e:
            return jsonify({"status": "error", "message": f"Could not parse body: {e}"}), 400

    # Start the long-running job in a separate thread and return immediately
    def target():
        run_trading_system(data)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()

    return jsonify({"status": "started", "message": "Execution started"}), 202


@app.route('/status')
def status():
    return jsonify({"is_running": running["is_running"]})


@app.route('/last_run_config')
def last_run_config():
    try:
        with open(LAST_RUN_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f, object_pairs_hook=OrderedDict)
        return jsonify(data)
    except Exception:
        return jsonify({}), 204


@app.route('/logs')
def get_logs():
    # return logs as a list (oldest first)
    with log_lock:
        items = list(logs)
    return jsonify({'logs': items})


@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    with log_lock:
        logs.clear()
    add_log('Logs cleared')
    return jsonify({'ok': True})


def stop_current_pg():
    """Attempt to stop the currently running Programgarden instance."""
    with current_pg_lock:
        pg = globals().get('current_pg')
        pg.stop()
    if pg is None:
        add_log('No Programgarden instance to stop')
        return False

    def _stop():
        try:
            # Programgarden.stop is async
            import asyncio
            asyncio.run(pg.stop())
            add_log('Programgarden.stop completed')
        except Exception as e:
            add_log(f'Error stopping Programgarden: {e}', level='ERROR')

    t = threading.Thread(target=_stop, daemon=True)
    t.start()
    return True


@app.route('/stop', methods=['POST'])
def stop_endpoint():
    ok = stop_current_pg()
    if ok:
        return jsonify({'status': 'stopping'}), 202
    return jsonify({'status': 'no_instance'}), 400


if __name__ == '__main__':
    ensure_last_run_config()
    app.run(host='127.0.0.1', port=5550, debug=True)
