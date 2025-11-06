#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Учебная реализация электронной подписи по FIPS-186 (DSA)
Без сторонних библиотек. Всё — от генерации p, q, g до подписи и проверки.
"""

import hashlib
import random

def is_prime(n, k=5):
    """Проверка простоты числа (тест Миллера–Рабина)."""
    if n < 2:
        return False

    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23]
    if n in small_primes:
        return True
    if any(n % p == 0 for p in small_primes):
        return False

    s, d = 0, n - 1
    while d % 2 == 0:
        s += 1
        d //= 2
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def gen_prime(bits):
    """Генерирует простое число заданной битовой длины."""
    while True:
        n = random.getrandbits(bits) | 1 | (1 << (bits - 1))
        if is_prime(n):
            return n

def sha256_of_file(filename):
    """Хеш SHA-256 файла (как целое число)."""
    h = hashlib.sha256()
    with open(filename, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return int.from_bytes(h.digest(), "big")

def generate_dsa_params():
    """Генерация параметров p, q, g."""
    print("Генерация параметров DSA...")
    q = gen_prime(16)
    while True:
        k = random.randint(2**15, 2**16)
        p = k * q + 1
        if is_prime(p):
            break
    while True:
        h = random.randint(2, p - 2)
        g = pow(h, (p - 1) // q, p)
        if g > 1:
            break
    print(f"Сгенерированы параметры:\n  p = {p}\n  q = {q}\n  g = {g}\n")
    return p, q, g


def generate_keys(p, q, g):
    """Генерация пары ключей DSA."""
    x = random.randint(1, q - 1)
    y = pow(g, x, p)
    print(f"Ключи созданы:\n  x (секретный) = {x}\n  y (открытый) = {y}\n")
    return x, y

def sign_file(filename, p, q, g, x):
    """Формирует подпись файла (r, s)."""
    H = sha256_of_file(filename)
    while True:
        k = random.randint(1, q - 1)
        r = pow(g, k, p) % q
        if r == 0:
            continue
        try:
            k_inv = pow(k, -1, q)
        except ValueError:
            continue
        s = (k_inv * (H + x * r)) % q
        if s != 0:
            break
    with open(filename + ".sig", "w") as f:
        f.write(f"{r}\n{s}\n")
    print(f"Файл подписан.\n  r={r}\n  s={s}\nПодпись сохранена в {filename}.sig\n")


def verify_file(filename, p, q, g, y):
    """Проверяет подпись файла."""
    try:
        with open(filename + ".sig", "r") as f:
            r = int(f.readline())
            s = int(f.readline())
    except Exception:
        print("Не удалось прочитать файл подписи.")
        return

    if not (0 < r < q and 0 < s < q):
        print("Неверные параметры подписи.")
        return

    H = sha256_of_file(filename)
    try:
        w = pow(s, -1, q)
    except ValueError:
        print("Не удаётся вычислить обратный элемент.")
        return
    u1 = (H * w) % q
    u2 = (r * w) % q
    v = ((pow(g, u1, p) * pow(y, u2, p)) % p) % q

    if v == r:
        print("Подпись ВЕРНА — файл не изменён.\n")
    else:
        print("Подпись НЕВЕРНА или файл был изменён.\n")


def main():
    params = None
    keys = None
    while True:
        print("\n====== ЭЛЕКТРОННАЯ ПОДПИСЬ (FIPS-186 / DSA) ======")
        print("1. Сгенерировать параметры (p, q, g)")
        print("2. Сгенерировать ключи (x, y)")
        print("3. Подписать файл")
        print("4. Проверить подпись")
        print("0. Выход")

        choice = input("Ваш выбор: ").strip()

        if choice == "1":
            params = generate_dsa_params()
        elif choice == "2":
            if not params:
                print("Сначала сгенерируйте параметры (пункт 1).")
                continue
            keys = generate_keys(*params)
        elif choice == "3":
            if not (params and keys):
                print("Сначала сгенерируйте параметры и ключи.")
                continue
            filename = input("Введите имя файла для подписи: ").strip()
            sign_file(filename, *params, keys[0])
        elif choice == "4":
            if not (params and keys):
                print("Сначала сгенерируйте параметры и ключи.")
                continue
            filename = input("Введите имя файла для проверки: ").strip()
            verify_file(filename, *params, keys[1])
        elif choice == "0":
            print("До свидания!")
            break
        else:
            print("Неверный выбор, попробуйте снова.")


if __name__ == "__main__":
    main()
