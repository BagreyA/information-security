"""
Fiat-Shamir идентификация — клиент/сервер однофайловый демонстрационный пример
Запуск:
  python fiat_shamir_client_server.py --server
  python fiat_shamir_client_server.py --client

Ключевые моменты реализации (для учебной демонстрации):
- Сервер хранит открытые ключи (n, v = s^2 mod n) в файле users.json.
- Клиент хранит секрет s локально (в файле client_secret.json) и никогда не отправляет его на сервер.
- Протокол: классический интерактивный протокол Фиата-Шамира
    1) Проказывающий (клиент) выбирает случайное r, отправляет x = r^2 mod n -> сервер
    2) Сервер присылает битовый вызов e (0 или 1) — можно повторить t раз
    3) Клиент отвечает y = r * s^e mod n
    4) Сервер проверяет y^2 == x * v^e (mod n)

"""
from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import random
import hashlib
import sys
import time
from typing import Tuple
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog

# ---------- Утилиты ----------
def int_to_bytes(n: int) -> bytes:
    """
    Преобразует целое число в байты для последующего хеширования.
    Используется в функции hash_int.
    """
    return n.to_bytes((n.bit_length() + 7) // 8 or 1, 'big')

def hash_int(*values) -> int:
    """
    Хеширует последовательность целых чисел SHA-256.
    Возвращает целое число из байтов хеша.
    Пример использования: создание уникальных идентификаторов или ключей.
    """
    h = hashlib.sha256()
    for v in values:
        h.update(int_to_bytes(v))
    return int.from_bytes(h.digest(), 'big')

def save_json(path: str, obj):
    """
    Сохраняет объект Python в JSON файл.
    Используется для хранения ключей пользователей и секретов.
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def load_json(path: str):
    """
    Загружает объект из JSON файла.
    Возвращает None, если файл не найден.
    """
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# ---------- Генерация демо-ключей ----------
def generate_demo_keypair(bits: int = 256) -> Tuple[int, int, int]:
    """
    Генерация демонстрационного набора ключей (n, s, v) для протокола Фиата-Шамира.
    - n = p * q (модуль)
    - s = секрет клиента
    - v = публичный ключ (v = s^2 mod n)
    Используется только для демонстрации (небезопасно для реальной криптографии)
    """
    def make_prime_candidate(kbits: int) -> int:
        """
        Генерация "демо" простого числа с заданной длиной в битах.
        Проверка делимости на малые простые числа для ускорения.
        """
        while True:
            candidate = random.getrandbits(kbits) | 1 | (1 << (kbits - 1))
            small_primes = [3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61]
            if all(candidate % p != 0 for p in small_primes):
                return candidate
    # Генерация простых чисел p и q
    p = make_prime_candidate(bits // 2)
    q = make_prime_candidate(bits // 2)
    n = p * q
    # Выбор случайного секрета s, взаимно простого с n
    s = random.randrange(2, n - 1)
    while __import__('math').gcd(s, n) != 1:
        s = random.randrange(2, n - 1)
    # Публичный ключ
    v = pow(s, 2, n)
    return n, s, v

# ---------- JSON-сообщения для TCP ----------
def send_json(sock: socket.socket, obj):
    """
    Отправка JSON-объекта через TCP сокет.
    Сначала отправляется длина данных (8 байт), затем сам JSON.
    """
    data = json.dumps(obj).encode('utf-8')
    length = len(data)
    sock.sendall(length.to_bytes(8, 'big'))
    sock.sendall(data)

def recv_json(sock: socket.socket):
    """
    Прием JSON-объекта через TCP сокет.
    Сначала читается длина, затем данные.
    """
    length_bytes = recvall(sock, 8)
    if not length_bytes:
        return None
    length = int.from_bytes(length_bytes, 'big')
    data = recvall(sock, length)
    if data is None:
        return None
    return json.loads(data.decode('utf-8'))

def recvall(sock: socket.socket, n: int) -> bytes | None:
    """
    Чтение точно n байт из сокета.
    Необходимо для корректного приема сообщений TCP.
    """
    data = b''
    while len(data) < n:
        try:
            packet = sock.recv(n - len(data))
        except ConnectionResetError:
            return None
        if not packet:
            return None
        data += packet
    return data

# ---------- Сервер ----------
class FiatShamirServer:
    """
    Серверная часть протокола Фиата-Шамира.
    Поддерживает регистрацию пользователей и интерактивную идентификацию.
    """
    gui = None  # для логирования
    def __init__(self, host='0.0.0.0', port=9000, users_file='users.json'):
        self.host = host
        self.port = port
        self.users_file = users_file
        self.users = self._load_users() # загрузка пользователей
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._stop = threading.Event() # событие для остановки сервера

    def _load_users(self):
        raw = load_json(self.users_file)
        if not raw:
            return {}
        return {u: {'n': int(v['n']), 'v': int(v['v'])} for u, v in raw.items()}

    def _save_users(self):
        save_json(self.users_file, self.users)

    def add_user(self, username: str, n: int, v: int):
        self.users[username] = {'n': n, 'v': v}
        self._save_users()

    def remove_user(self, username: str):
        if username in self.users:
            del self.users[username]
            self._save_users()

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()

    def stop(self):
        self._stop.set()
        try:
            self.sock.close()
        except OSError:
            pass

    def _accept_loop(self):
        """
        Основной цикл приема клиентов
        """
        while not self._stop.is_set():
            try:
                client, addr = self.sock.accept()
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(client, addr), daemon=True).start()

    def _handle_client(self, client_sock: socket.socket, addr):
        """
        Обработка протокола для одного клиента
        """
        def _log(*a):
            msg = f"[{time.strftime('%H:%M:%S')}] " + ' '.join(str(x) for x in a)
            print(msg)
            if self.gui and hasattr(self.gui, 'txt_log'):
                self.gui.txt_log.insert('end', msg + '\n')
                self.gui.txt_log.see('end')
        _log('Клиент подключился с', addr)

        try:
            req = recv_json(client_sock)
            if not req or req.get('type') != 'hello':
                client_sock.close()
                return
            username = req['username']
            if username not in self.users:
                _log('Неизвестный пользователь:', username)
                send_json(client_sock, {'type': 'error', 'message': 'Unknown user'})
                client_sock.close()
                return
            send_json(client_sock, {'type': 'params', 'n': str(self.users[username]['n']), 'v': str(self.users[username]['v'])})

            rounds = req.get('rounds', 5)
            success_all = True

            for i in range(rounds):
                msg = recv_json(client_sock)
                if not msg or msg.get('type') != 'x':
                    success_all = False
                    break
                x = int(msg['x'])
                _log('Получено x =', x)

                e = random.randint(0, 1)
                _log('Отправляю вызов e =', e)
                send_json(client_sock, {'type': 'e', 'e': e})

                reply = recv_json(client_sock)
                if not reply or reply.get('type') != 'y':
                    success_all = False
                    break
                y = int(reply['y'])
                _log('Получено y =', y)

                n = self.users[username]['n']
                v = self.users[username]['v']
                left = pow(y, 2, n)
                right = (x * pow(v, e, n)) % n
                ok = (left == right)
                _log(f'Проверка: left={left} right={right} →', 'OK' if ok else 'FAILED')

                send_json(client_sock, {'type': 'result', 'ok': ok, 'round': i + 1})

                if not ok:
                    success_all = False

            _log('Итоговая проверка завершена. accepted =', success_all)
            send_json(client_sock, {'type': 'final', 'accepted': success_all})
        finally:
            client_sock.close()

# ---------- Клиент ----------
class FiatShamirClientGUI:
    """
    Клиентская часть протокола Фиата-Шамира с графическим интерфейсом.
    """
    def __init__(self, server_host='127.0.0.1', server_port=9000):
        self.server_host = server_host
        self.server_port = server_port
        self.username = None
        self.n = None
        self.v = None
        self.s = None
        self.r = None
        self.x = None
        self.e = None
        self.y = None
        self.rounds = 5

        self.root = tk.Tk()
        self.root.title('Fiat-Shamir demo — клиент')
        self._build_gui()
        self.sock = None
        self._network_thread = None

    def _build_gui(self):
        frm_top = ttk.Frame(self.root, padding=8)
        frm_top.pack(fill=tk.X)

        ttk.Label(frm_top, text='Логин:').grid(row=0, column=0, sticky=tk.W)
        self.entry_user = ttk.Entry(frm_top)
        self.entry_user.grid(row=0, column=1, sticky=tk.W)

        ttk.Button(frm_top, text='Загрузить/создать ключи', command=self._on_gen_or_load).grid(row=0, column=2, padx=6)
        ttk.Label(frm_top, text='Раундов:').grid(row=0, column=3, sticky=tk.W, padx=(10,0))
        self.spin_rounds = tk.Spinbox(frm_top, from_=1, to=20, width=4)
        self.spin_rounds.grid(row=0, column=4, sticky=tk.W)

        ttk.Button(frm_top, text='Подключиться и аутентифицироваться', command=self._start_protocol).grid(row=1, column=0, columnspan=5, pady=8)

        self.txt = scrolledtext.ScrolledText(self.root, width=80, height=20)
        self.txt.pack(padx=8, pady=6)

        frm_bottom = ttk.Frame(self.root, padding=8)
        frm_bottom.pack(fill=tk.X)
        ttk.Button(frm_bottom, text='Очистить лог', command=lambda: self.txt.delete('1.0', tk.END)).pack(side=tk.LEFT)
        ttk.Button(frm_bottom, text='Закрыть', command=self._on_close).pack(side=tk.RIGHT)

    def _log(self, *parts):
        msg = f"[{time.strftime('%H:%M:%S')}] " + ' '.join(str(p) for p in parts)
        print(msg)
        self.txt.insert(tk.END, msg + '\n')
        self.txt.see(tk.END)

    def _on_gen_or_load(self):
        username = self.entry_user.get().strip()
        if not username:
            messagebox.showwarning('Введите логин', 'Введите логин перед генерацией/загрузкой ключей.')
            return
        self.username = username
        client_secret_file = f'client_secret_{username}.json'
        data = load_json(client_secret_file)
        if data:
            self.s = int(data['s'])
            self.n = int(data['n'])
            self.v = int(data['v'])
            self._log('Загружены локальные ключи для', username)
            self._log(f'n={self.n}', f'v={self.v}', 'секрет скрыт')
        else:
            if not messagebox.askyesno('Создать ключи', 'Ключей не найдено. Создать новый набор ключей (демо)?'):
                return
            n, s, v = generate_demo_keypair(bits=256)
            self.n = n
            self.s = s
            self.v = v
            save_json(client_secret_file, {'n': str(n), 's': str(s), 'v': str(v)})
            self._log('Сгенерированы и сохранены локальные ключи в', client_secret_file)
            self._log(f'n={n}', f'v={v}', 'секрет сохранён локально')
            messagebox.showinfo('Регистрация', f'Публичный ключ сохранён локально. Зарегистрируйте пользователя {username} на сервере со значением v={v} и n={n}.')

    def _start_protocol(self):
        if not self.username:
            self.username = self.entry_user.get().strip()
        if not self.username:
            messagebox.showwarning('Введите логин', 'Введите логин перед аутентификацией.')
            return
        try:
            self.rounds = int(self.spin_rounds.get())
        except Exception:
            self.rounds = 5
        self._network_thread = threading.Thread(target=self._run_protocol, daemon=True)
        self._network_thread.start()

    def _run_protocol(self):
        try:
            self._log('Подключение к серверу', f'{self.server_host}:{self.server_port}')
            with socket.create_connection((self.server_host, self.server_port), timeout=10) as sock:
                self.sock = sock
                send_json(sock, {'type': 'hello', 'username': self.username, 'rounds': self.rounds})
                resp = recv_json(sock)
                if not resp or resp.get('type') == 'error':
                    self._log('Сервер ответил ошибкой:', resp.get('message') if resp else 'no response')
                    return
                if resp.get('type') != 'params':
                    self._log('Ожидаемые параметры не получены от сервера')
                    return
                self.n = int(resp['n'])
                self.v = int(resp['v'])
                self._log('Получены публичные параметры от сервера:')
                self._log(f'n={self.n}', f'v={self.v}')

                client_secret_file = f'client_secret_{self.username}.json'
                data = load_json(client_secret_file)
                if not data:
                    self._log('Локальный секрет не найден. Аутентификация невозможна.')
                    return
                self.s = int(data['s'])
                if pow(self.s, 2, self.n) != self.v:
                    self._log('Локальный секрет не соответствует публичному ключу (v).')
                    return

                success_all = True
                for i in range(self.rounds):
                    self.r = random.randrange(2, self.n - 1)
                    self.x = pow(self.r, 2, self.n)
                    self._log(f'Раунд {i+1}: выбран r. Отправляю x =', self.x)
                    send_json(sock, {'type': 'x', 'x': str(self.x)})

                    msg = recv_json(sock)
                    if not msg or msg.get('type') != 'e':
                        self._log('Не получил бит вызова от сервера.')
                        success_all = False
                        break
                    self.e = int(msg['e'])
                    self._log('Сервер прислал вызов e =', self.e)

                    self.y = self.r if self.e == 0 else (self.r * self.s) % self.n
                    self._log('Посылаю ответ y = r * s^e mod n =', self.y)
                    send_json(sock, {'type': 'y', 'y': str(self.y)})

                    res = recv_json(sock)
                    if not res or res.get('type') != 'result':
                        self._log('Не получил результат проверки от сервера.')
                        success_all = False
                        break
                    ok = bool(res['ok'])
                    self._log(f'Сервер проверил раунд {res.get("round")}:', 'OK' if ok else 'FAILED')
                    if not ok:
                        success_all = False

                final = recv_json(sock)
                if final and final.get('type') == 'final':
                    accepted = final.get('accepted')
                    self._log('Аутентификация завершена. Принят:' , accepted)
                else:
                    self._log('Не получили финального сообщения от сервера.')

        except Exception as ex:
            self._log('Ошибка сети:', ex)
        finally:
            self.sock = None

    def _on_close(self):
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

# ---------- GUI сервера ----------
class ServerGUI:
    def __init__(self, server: FiatShamirServer):
        self.server = server
        self.server.gui = self
        self.root = tk.Tk()
        self.root.title('Fiat-Shamir demo — сервер')
        self._build_gui()
        self.server.start()

    def _build_gui(self):
        frm = ttk.Frame(self.root, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text='Зарегистрированные пользователи (login : v)').pack(anchor=tk.W)
        self.txt_users = scrolledtext.ScrolledText(frm, width=60, height=8)
        self.txt_users.pack(pady=4)
        frm_ops = ttk.Frame(frm)
        frm_ops.pack(fill=tk.X)

        ttk.Button(frm_ops, text='Обновить список', command=self._refresh_users).pack(side=tk.LEFT)
        ttk.Button(frm_ops, text='Добавить пользователя (вручную)', command=self._add_user_prompt).pack(side=tk.LEFT, padx=6)
        ttk.Button(frm_ops, text='Удалить пользователя', command=self._del_user_prompt).pack(side=tk.LEFT)

        ttk.Separator(frm, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(frm, text='Логи сервера:').pack(anchor=tk.W)
        self.txt_log = scrolledtext.ScrolledText(frm, width=80, height=12)
        self.txt_log.pack(pady=4)

        frm_bottom = ttk.Frame(frm)
        frm_bottom.pack(fill=tk.X)
        ttk.Button(frm_bottom, text='Очистить логи', command=lambda: self.txt_log.delete('1.0', tk.END)).pack(side=tk.LEFT)
        ttk.Button(frm_bottom, text='Закрыть сервер', command=self._on_close).pack(side=tk.RIGHT)

        self._refresh_users()

    def _refresh_users(self):
        self.txt_users.delete('1.0', tk.END)
        for user, vals in self.server.users.items():
            self.txt_users.insert(tk.END, f'{user} : n={vals["n"]} v={vals["v"]}\n')

    def _add_user_prompt(self):
        dialog = AddUserDialog(self.root)
        self.root.wait_window(dialog.top)
        if dialog.result:
            username, n_str, v_str = dialog.result
            try:
                n = int(n_str)
                v = int(v_str)
                self.server.add_user(username, n, v)
                self._refresh_users()
                messagebox.showinfo('Добавлено', f'Пользователь {username} добавлен.')
            except Exception as ex:
                messagebox.showerror('Ошибка', f'Невозможно добавить: {ex}')

    def _del_user_prompt(self):
        username = simpledialog.askstring('Удалить', 'Логин для удаления:')
        if username:
            self.server.remove_user(username)
            self._refresh_users()

    def _on_close(self):
        self.server.stop()
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

class AddUserDialog:
    def __init__(self, parent):
        top = self.top = tk.Toplevel(parent)
        top.title('Добавить пользователя')
        ttk.Label(top, text='Логин').grid(row=0, column=0)
        ttk.Label(top, text='n (целое)').grid(row=1, column=0)
        ttk.Label(top, text='v (целое)').grid(row=2, column=0)
        self.e_user = ttk.Entry(top)
        self.e_n = ttk.Entry(top)
        self.e_v = ttk.Entry(top)
        self.e_user.grid(row=0, column=1)
        self.e_n.grid(row=1, column=1)
        self.e_v.grid(row=2, column=1)
        ttk.Button(top, text='Добавить', command=self._on_add).grid(row=3, column=0)
        ttk.Button(top, text='Отмена', command=self._on_cancel).grid(row=3, column=1)
        self.result = None

    def _on_add(self):
        self.result = (self.e_user.get().strip(), self.e_n.get().strip(), self.e_v.get().strip())
        self.top.destroy()

    def _on_cancel(self):
        self.top.destroy()

def main():
    parser = argparse.ArgumentParser(description='Fiat-Shamir demo client/server')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--server', action='store_true', help='Запустить сервер с GUI для регистрации пользователей')
    group.add_argument('--client', action='store_true', help='Запустить клиентское GUI для аутентификации')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=9000)
    args = parser.parse_args()

    if args.server:
        server = FiatShamirServer(host=args.host, port=args.port)
        gui = ServerGUI(server)
        gui.run()
    elif args.client:
        client = FiatShamirClientGUI(server_host=args.host, server_port=args.port)
        client.run()

if __name__ == '__main__':
    main()
