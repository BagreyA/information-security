"""
Демонстрация голосования с использованием слепых подписей (Tkinter)

Однофайловая демонстрация слепых подписей по методу Дэвида Чаума
(Chaum-style RSA blind signatures) для анонимного голосования.

Клиент и сервер реализованы как отдельные классы, но работают
в одном процессе для удобства демонстрации и интерактивности.
Графический интерфейс (GUI) показывает все внутренние параметры:
RSA-ключи, множитель ослепления, затемнённое сообщение,
подписи и т. д.

Использование: python3 blind_sign_voting.py

Внешние библиотеки не требуются (только Python 3.8+).
Программа предназначена исключительно для учебных целей —
используемая криптография упрощена и не является безопасной
для реального применения.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import random
import hashlib
import math
import secrets
import csv

# ---------------------- Вспомогательные криптографические функции ----------------------

def is_prime(n, k=10):
    # Тест Миллера–Рабина на простоту числа
    if n < 2:
        return False
    small_primes = [2,3,5,7,11,13,17,19,23,29]
    for p in small_primes:
        if n % p == 0:
            return n == p
    # Разложим n-1 как 2^r * d
    r = 0
    d = n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    for _ in range(k):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        composite = True
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                composite = False
                break
        if composite:
            return False
    return True

def gen_prime(bits=256):
# Генерация случайного простого числа заданной длины в битах
    while True:
        p = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if is_prime(p):
            return p

def egcd(a, b):
# Расширенный алгоритм Евклида
    if b == 0:
        return (a, 1, 0)
    g, x1, y1 = egcd(b, a % b)
    return (g, y1, x1 - (a // b) * y1)

def modinv(a, m):
# Модульный обратный элемент (a^(-1) mod m)
    g, x, y = egcd(a, m)
    if g != 1:
        raise ValueError('Обратный элемент не существует')
    return x % m

def sha256_int(data: bytes) -> int:
# Хэш SHA-256 → целое число
    h = hashlib.sha256()
    h.update(data)
    return int.from_bytes(h.digest(), 'big')

# ---------------------- Классы сервера и клиента ----------------------

class Server:
    """Сервер хранит RSA-ключи и подписывает затемнённые сообщения.

    Также он проверяет финальные бюллетени (message + signature + ballot_text).
    В демонстрации сервер подписывает любое затемнённое сообщение.
    В реальной системе голосования подписание должно происходить
    только после проверки личности и права на голосование.
    """
    def __init__(self, key_bits=512):
        self.key_bits = key_bits
        self._generate_keys()
        # Храним принятые бюллетени в виде кортежей (message_int, signature_int, ballot_text)
        self.received_ballots = []

    def _generate_keys(self):
        # Генерация пары RSA-ключей (p, q, n, e, d)
        p = gen_prime(bits=self.key_bits // 2)
        q = gen_prime(bits=self.key_bits // 2)
        while q == p:
            q = gen_prime(bits=self.key_bits // 2)
        n = p * q
        phi = (p - 1) * (q - 1)
        e = 65537
        if math.gcd(e, phi) != 1:
            # Редкий случай — подбираем другой e
            e = 3
            while math.gcd(e, phi) != 1:
                e += 2
        d = modinv(e, phi)
        self.p, self.q, self.n, self.e, self.d = p, q, n, e, d

    def sign_blinded(self, blinded_int: int) -> int:
        # Подпись затемнённого сообщения: s' = (blinded_int)^d mod n
        return pow(blinded_int, self.d, self.n)

    def verify_ballot(self, message_int: int, signature_int: int, ballot_text: str = None) -> bool:
        """
        Надёжная проверка: если передан ballot_text, сервер пересчитывает m_from_text
        и проверяет подпись относительно этого значения. Клиентский message_int
        используется только для логирования, но не для проверки.
        """
        if ballot_text is None:
            return False

        # Пересчитаем m из текста
        try:
            m_from_text = sha256_int(ballot_text.encode('utf8')) % self.n
        except Exception:
            return False

        # Проверяем подпись: signature^e mod n == m_from_text
        lhs = pow(signature_int, self.e, self.n)
        ok = lhs == m_from_text

        if ok:
            stored = (m_from_text, signature_int, ballot_text)
            if stored not in self.received_ballots:
                self.received_ballots.append(stored)
                return True
            else:
                # Дубликат бюллетеня
                return False
        return False

class Client:
    """Клиент формирует бюллетень, ослепляет его, получает подпись сервера,
    снимает ослепление и затем отправляет бюллетень обратно на сервер.
    """
    def __init__(self, server: Server):
        self.server = server
        self.choice = None
        self.r = None
        self.blinded = None
        self.signed_blinded = None
        self.signature = None
        self.message_int = None

    def create_ballot(self, choice_text: str):
        # Текст бюллетеня: CHOICE + случайный идентификатор для уникальности
        nonce = secrets.token_hex(8)
        ballot_text = f"CHOICE:{choice_text};NONCE:{nonce}"
        self.choice = choice_text
        self.ballot_text = ballot_text
        self.message_int = sha256_int(ballot_text.encode('utf8')) % self.server.n
        return ballot_text

    def pick_blinding_factor(self):
        # Генерация множителя ослепления r (взаимно простого с n)
        n = self.server.n
        while True:
            r = secrets.randbelow(n - 2) + 2
            if math.gcd(r, n) == 1:
                self.r = r
                return r

    def blind_message(self):
        # Ослепление сообщения: m' = (m * r^e) mod n
        if self.message_int is None:
            raise ValueError('Сообщение не задано')
        if self.r is None:
            self.pick_blinding_factor()
        n = self.server.n
        e = self.server.e
        blinded = (self.message_int * pow(self.r, e, n)) % n
        self.blinded = blinded
        return blinded

    def request_signature(self):
        # Запрос подписи у сервера (сервер подписывает затемнённое сообщение)
        if self.blinded is None:
            raise ValueError('Затемнённое сообщение не вычислено')
        s_blinded = self.server.sign_blinded(self.blinded)
        self.signed_blinded = s_blinded
        return s_blinded

    def unblind(self):
        # Снятие ослепления: s = s' * r^(-1) mod n
        if self.signed_blinded is None or self.r is None:
            raise ValueError('Отсутствуют данные для снятия ослепления')
        n = self.server.n
        r_inv = modinv(self.r, n)
        signature = (self.signed_blinded * r_inv) % n
        self.signature = signature
        return signature

    def verify_local(self):
        # Локальная проверка подписи клиента: s^e mod n == m
        if self.signature is None:
            return False
        lhs = pow(self.signature, self.server.e, self.server.n)
        return lhs == self.message_int

# ---------------------- GUI на Tkinter ----------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Демонстрация голосования со слепой подписью')
        self.geometry('1200x760')
        self.server = Server(key_bits=512)
        self.client = Client(server=self.server)
        self._create_widgets()

    def _create_widgets(self):
        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True, padx=10, pady=10)

        # Слева: Клиент
        client_frame = ttk.LabelFrame(frm, text='Клиент (избиратель)')
        client_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        frm.columnconfigure(0, weight=1)

        # Варианты голосования
        self.vote_var = tk.StringVar(value='Да')
        opts = ['Да', 'Нет', 'Воздержался']
        ttk.Label(client_frame, text='Выберите вариант:').grid(row=0, column=0, sticky='w')
        for i, o in enumerate(opts):
            ttk.Radiobutton(client_frame, text=o, value=o, variable=self.vote_var).grid(row=1, column=i, sticky='w')

        # Кнопки действий клиента    
        ttk.Button(client_frame, text='Сформировать бюллетень', command=self.form_ballot).grid(row=2, column=0, pady=6)
        ttk.Button(client_frame, text='Выбрать/сгенерировать r (слепящий множитель)', command=self.pick_r).grid(row=2, column=1, pady=6)
        ttk.Button(client_frame, text='Затемнить бюллетень (blind)', command=self.blind).grid(row=2, column=2, pady=6)
        ttk.Button(client_frame, text='Запросить подпись у сервера', command=self.request_signature).grid(row=3, column=0, pady=6)
        ttk.Button(client_frame, text='Распознать подпись (unblind)', command=self.unblind).grid(row=3, column=1, pady=6)
        ttk.Button(client_frame, text='Локальная проверка подписи', command=self.verify_local).grid(row=3, column=2, pady=6)
        ttk.Button(client_frame, text='Отправить бюллетень на сервер', command=self.send_to_server).grid(row=4, column=0, pady=6)
        ttk.Button(client_frame, text='Подделать бюллетень', command=self.tamper_ballot).grid(row=4, column=1, pady=6)

        # Вывод информации клиента
        self.client_text = scrolledtext.ScrolledText(client_frame, width=80, height=22)
        self.client_text.grid(row=5, column=0, columnspan=3, padx=5, pady=5)
        self._print_client('Клиент готов. Нажмите "Сформировать бюллетень".')

        # Справа: Сервер
        server_frame = ttk.LabelFrame(frm, text='Сервер (избирательная комиссия)')
        server_frame.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
        frm.columnconfigure(1, weight=1)

        # Кнопки и вывод информации сервера
        ttk.Button(server_frame, text='Сгенерировать ключи сервера (новые)', command=self.regen_keys).grid(row=0, column=0, pady=6)
        ttk.Label(server_frame, text='Параметры публичного ключа (n, e) и приватного (d) — показаны ниже:').grid(row=1, column=0, sticky='w')
        self.server_text = scrolledtext.ScrolledText(server_frame, width=70, height=18)
        self.server_text.grid(row=2, column=0, padx=5, pady=5)
        self._print_server('Сервер готов. Ключи сгенерированы автоматически.')

        ttk.Button(server_frame, text='Проверить принятые бюллетени', command=self.show_received).grid(row=3, column=0, pady=6)
        ttk.Button(server_frame, text='Экспорт в CSV', command=self.export_received_csv).grid(row=4, column=0, pady=6)

        # Статусная строка
        self.status = tk.StringVar(value='Готово')
        ttk.Label(self, textvariable=self.status).pack(side='bottom', fill='x')

        # Первоначальный вывод ключей сервера
        self._show_server_keys()

    # ----------------- Действия клиента -----------------
    def _print_client(self, *lines):
        self.client_text.insert('end', '\n'.join(map(str, lines)) + '\n')
        self.client_text.see('end')

    def _print_server(self, *lines):
        self.server_text.insert('end', '\n'.join(map(str, lines)) + '\n')
        self.server_text.see('end')

    def form_ballot(self):
        choice = self.vote_var.get()
        ballot = self.client.create_ballot(choice)
        self._print_client('Сформирован бюллетень:', ballot)
        self._print_client('Hash->m (mod n) =', self.client.message_int)
        self.status.set('Бюллетень сформирован')

    def pick_r(self):
        r = self.client.pick_blinding_factor()
        self._print_client('Сгенерирован блайндинг r =', r)
        self._print_client('gcd(r, n) =', math.gcd(r, self.server.n))
        self.status.set('Блайндинг r сгенерирован')

    def blind(self):
        try:
            b = self.client.blind_message()
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))
            return
        self._print_client('Затемнённый (blinded) m\' =', b)
        self._print_client('Отправляется на сервер для подписи...')
        self.status.set('Бюллетень затемнён')

    def request_signature(self):
        try:
            s_blinded = self.client.request_signature()
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))
            return
        self._print_client('Сервер вернул подпись затемнённого сообщения s\' =', s_blinded)
        self.status.set('Подпись получена')

    def unblind(self):
        try:
            sig = self.client.unblind()
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))
            return
        self._print_client('Распознанная (unblinded) подпись s =', sig)
        self._print_client('Проверочно: s^e mod n =', pow(sig, self.server.e, self.server.n))
        self._print_client('ожидаемый m =', self.client.message_int)
        self.status.set('Подпись распознана (unblinded)')

    def verify_local(self):
        ok = self.client.verify_local()
        self._print_client('Локальная проверка подписи:', 'OK' if ok else 'Ошибка')
        self.status.set('Локальная проверка выполнена')

    def tamper_ballot(self):
        """Демонстрация: изменение текста бюллетеня ПОСЛЕ получения подписи.

        Важно: мы *не пересчитываем* message_int или подпись — это имитирует
        поведение злоумышленника: изменяем содержимое, но оставляем подпись от
        оригинального текста. При проверке сервером несоответствие будет обнаружено.
        """
        if not hasattr(self.client, 'ballot_text') or self.client.ballot_text is None:
            messagebox.showerror('Ошибка', 'Сначала сформируйте бюллетень и получите подпись.')
            return
        # Изменяем текст бюллетеня: меняем выбор (для демонстрации). message_int остаётся прежним.
        old = self.client.ballot_text
        if 'CHOICE:Да' in old:
            new = old.replace('CHOICE:Да', 'CHOICE:Нет')
        elif 'CHOICE:Нет' in old:
            new = old.replace('CHOICE:Нет', 'CHOICE:Да')
        else:
            new = old + ';TAMPERED'
        self.client.ballot_text = new
        # НЕ обновляем self.client.message_int -> злоумышленник
        self._print_client('*** ВНИМАНИЕ: бюллетень подделан ***')
        self._print_client('Старый текст:', old)
        self._print_client('Новый текст (подделан):', new)
        self._print_client('Примечание: message_int и подпись остались прежними — сервер определит несоответствие при отправке.')
        self.status.set('Бюллетень подделан')

    def send_to_server(self):
        if self.client.signature is None or self.client.message_int is None:
            messagebox.showerror('Ошибка', 'Нет подписанного бюллетеня для отправки')
            return

        ballot_text = getattr(self.client, 'ballot_text', None)
        ok = self.server.verify_ballot(self.client.message_int, self.client.signature, ballot_text)

        if ok:
            self._print_server('Принят бюллетень: ', ballot_text if ballot_text is not None else '<нет текста>')
            self._print_server('message_int (клиент) =', self.client.message_int)
            self._print_server('signature =', self.client.signature)
            self.status.set('Бюллетень принят сервером')
        else:
            # Дополнительная отладочная информация
            try:
                m_from_text = sha256_int(ballot_text.encode('utf8')) % self.server.n if ballot_text is not None else None
            except Exception:
                m_from_text = '<ошибка при хэше>'
            self._print_server('Отклонён бюллетень (несоответствие подписи/текста или дубликат)')
            self._print_server('Текст, присланный сейчас:', ballot_text)
            self._print_server('message_int (который прислал клиент) =', self.client.message_int)
            self._print_server('message_int (пересчитан по тексту) =', m_from_text)
            self._print_server('signature =', self.client.signature)
            self.status.set('Отказано в принятии')

    # ----------------- Действия сервера -----------------
    def regen_keys(self):
        self.server = Server(key_bits=512)
        self.client.server = self.server
        self.server_text.delete('1.0', 'end')
        self._show_server_keys()
        self._print_client('Внимание: ключи сервера обновлены — предыдущие подписи станут недействительны.')
        self.status.set('Ключи сервера сгенерированы заново')

    def _show_server_keys(self):
        self.server_text.insert('end', f'n = {self.server.n}\n')
        self.server_text.insert('end', f'e = {self.server.e}\n')
        self.server_text.insert('end', f'd = {self.server.d}\n')
        self.server_text.insert('end', f'p = {self.server.p}\n')
        self.server_text.insert('end', f'q = {self.server.q}\n')
        self.server_text.insert('end', '---\n')
        self.server_text.see('end')

    def show_received(self):
        """Показать все принятые сервером бюллетени"""
        if not self.server.received_ballots:
            messagebox.showinfo('Принятые бюллетени', 'Пока нет принятых бюллетеней')
            return
        s = '\n'.join([f'Бюллетень {i+1}: message={m}, signature={sig}, text={txt}' 
                       for i, (m, sig, txt) in enumerate(self.server.received_ballots)])
        messagebox.showinfo('Принятые бюллетени', s)

    def export_received_csv(self):
        """Экспорт принятых бюллетеней в CSV файл"""
        if not self.server.received_ballots:
            messagebox.showinfo('Экспорт', 'Нет принятых бюллетеней для экспорта.')
            return
        fpath = filedialog.asksaveasfilename(defaultextension='.csv',
                                             filetypes=[('CSV файлы','*.csv'), ('Все файлы','*.*')],
                                             title='Сохранить принятые бюллетени')
        if not fpath:
            return
        with open(fpath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['message_int','signature','ballot_text'])
            for m, sig, txt in self.server.received_ballots:
                writer.writerow([str(m), str(sig), txt if txt is not None else ""])
        messagebox.showinfo('Экспорт', f'Экспортировано {len(self.server.received_ballots)} бюллетеней в {fpath}')


if __name__ == '__main__':
    app = App()
    app.mainloop()
