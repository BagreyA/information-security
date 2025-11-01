import hashlib
import json
import random
from math import gcd
import os

def mod_inverse(a, m):
    """Обратный элемент по модулю m"""
    g, x, y = extended_gcd(a, m)
    if g != 1:
        raise ValueError("Обратного элемента не существует")
    return x % m

def extended_gcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x1, y1 = extended_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1

def is_prime(n, k=10):
    """Проверка простоты числа тестом Миллера-Рабина"""
    if n < 2:
        return False
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]:
        if n % p == 0:
            return n == p
    r, s = 0, n - 1
    while s % 2 == 0:
        r += 1
        s //= 2
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, s, n)
        if x in (1, n - 1):
            continue
        for __ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def generate_prime(bits=256):
    """Генерация простого числа"""
    while True:
        n = random.getrandbits(bits)
        n |= 1
        if is_prime(n):
            return n

def generate_keys(bits=256):
    print("Генерация ключей, подождите...")
    p = generate_prime(bits)
    g = random.randint(2, p - 2)
    x = random.randint(2, p - 2)
    y = pow(g, x, p)

    with open("private_key.json", "w") as f:
        json.dump({"p": p, "g": g, "x": x}, f)
    with open("public_key.json", "w") as f:
        json.dump({"p": p, "g": g, "y": y}, f)

    print("Ключи сгенерированы и сохранены:")
    print("   = public_key.json — публичный ключ")
    print("   = private_key.json — секретный ключ")

def sign_file():
    filename = input("Введите путь к файлу для подписи: ").strip()
    if not os.path.exists(filename):
        print("Файл не найден.")
        return

    key_path = input("Введите путь к секретному ключу (private_key.json): ").strip()
    if not os.path.exists(key_path):
        print("Файл ключа не найден.")
        return

    with open(filename, "rb") as f:
        file_data = f.read()
    with open(key_path, "r") as f:
        key_data = json.load(f)

    p = key_data["p"]
    g = key_data["g"]
    x = key_data["x"]

    hash_bytes = hashlib.sha256(file_data).digest()
    signature = []

    print("Подписание файла...")
    for m in hash_bytes:
        while True:
            k = random.randint(2, p - 2)
            if gcd(k, p - 1) == 1:
                break
        r = pow(g, k, p)
        s = (mod_inverse(k, p - 1) * (m - x * r)) % (p - 1)
        signature.append((r, s))

    sig_filename = filename + ".sig"
    with open(sig_filename, "w") as f:
        json.dump({"p": p, "g": g, "signature": signature}, f)

    print(f"Файл успешно подписан. Подпись сохранена в '{sig_filename}'")

def verify_file():
    filename = input("Введите путь к файлу для проверки: ").strip()
    sig_path = input("Введите путь к файлу подписи (.sig): ").strip()
    pub_path = input("Введите путь к открытому ключу (public_key.json): ").strip()

    if not all(os.path.exists(p) for p in [filename, sig_path, pub_path]):
        print("Один из файлов не найден.")
        return

    with open(filename, "rb") as f:
        file_data = f.read()
    with open(sig_path, "r") as f:
        sig_data = json.load(f)
    with open(pub_path, "r") as f:
        pub_data = json.load(f)

    p = pub_data["p"]
    g = pub_data["g"]
    y = pub_data["y"]
    signature = sig_data["signature"]
    hash_bytes = hashlib.sha256(file_data).digest()

    print("Проверка подписи...")
    for m, (r, s) in zip(hash_bytes, signature):
        left = (pow(y, r, p) * pow(r, s, p)) % p
        right = pow(g, m, p)
        if left != right:
            print("Подпись недействительна.")
            return

    print("Подпись верна.")

def main():
    while True:
        print("\n==============================")
        print("   ЭЛЕКТРОННАЯ ПОДПИСЬ ЭЛЬ-ГАМАЛЯ")
        print("==============================")
        print("1. Сгенерировать ключи")
        print("2. Подписать файл")
        print("3. Проверить подпись")
        print("4. Выход")
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            generate_keys()
        elif choice == "2":
            sign_file()
        elif choice == "3":
            verify_file()
        elif choice == "4":
            print("Выход из программы.")
            break
        else:
            print("Неверный выбор, попробуйте снова.")

if __name__ == "__main__":
    main()
