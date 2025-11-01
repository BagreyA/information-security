"""
Функции:
- mod_pow(a, x, p): быстрое возведение в степень по модулю, возвращает a^x mod p.
  Поддерживает отрицательные x (через модульную обратную при существовании).
- mod_inv(a, p): модульная обратная числа a по модулю p (возвращает x: a*x ≡ 1 (mod p)),
  либо возбуждает ValueError, если обратной не существует.
- is_probable_prime(n, k=5): вероятностный тест простоты (Miller–Rabin).
- is_probable_prime_fermat(n, k=5): тест простоты Ферма с высокой вероятностью.
- Добавлена функция обобщённого алгоритма Евклида для нахождения НОД(a, b) и
коэффициентов x, y из уравнения a*x + b*y = НОД(a, b).

Меню:
1) Возведение в степень по модулю
2) Найти обратный элемент
3) Проверка числа на простоту
4) Проверка числа на простоту (Ферма)
5) Обобщённый алгоритм Евклида (НОД + x, y)
0) Выход
"""

import random
from typing import Tuple

# -------------------------
# Core algorithms
# -------------------------

def mod_pow(a: int, x: int, p: int) -> int:
    if p <= 0:
        raise ValueError("Модуль p должен быть положительным целым числом.")
    a = a % p
    if p == 1:
        return 0
    if x < 0:
        inv = mod_inv(a, p)
        x = -x
        a = inv
    result = 1 % p
    base = a % p
    exp = x
    while exp > 0:
        if exp & 1:
            result = (result * base) % p
        base = (base * base) % p
        exp >>= 1
    return result

def extended_gcd(a: int, b: int) -> Tuple[int,int,int]:
    if b == 0:
        return (abs(a), 1 if a >= 0 else -1, 0)
    g, x1, y1 = extended_gcd(b, a % b)
    x = y1
    y = x1 - (a // b) * y1
    return (g, x, y)

def mod_inv(a: int, p: int) -> int:
    if p <= 0:
        raise ValueError("Модуль p должен быть положительным целым числом.")
    a = a % p
    g, x, _ = extended_gcd(a, p)
    if g != 1:
        raise ValueError(f"Обратной не существует, gcd({a},{p}) = {g} ≠ 1.")
    return x % p

def is_probable_prime(n: int, k: int = 5) -> bool:
    """Вероятностный тест Миллера–Рабина"""
    if n < 2:
        return False
    small_primes = [2,3,5,7,11,13,17,19,23,29]
    for p in small_primes:
        if n == p:
            return True
        if n % p == 0:
            return False
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = mod_pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        composite = True
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                composite = False
                break
        if composite:
            return False
    return True

def is_probable_prime_fermat(n: int, k: int = 5) -> bool:
    """Вероятностный тест простоты Ферма"""
    if n < 2:
        return False
    for _ in range(k):
        a = random.randint(2, n - 2)
        if mod_pow(a, n - 1, n) != 1:
            return False
    return True  # простое

def generalized_euclid(a: int = None, b: int = None, prime_only=False) -> Tuple[int,int,int,int,int]:
    if a is None or b is None:
        print("Выберите вариант генерации a и b:")
        print("1) Ввести с клавиатуры")
        print("2) Случайные числа")
        print("3) Случайные простые числа")
        choice = input("Ваш выбор: ").strip()
        if choice == "1":
            a = int(input("Введите a: "))
            b = int(input("Введите b: "))
        elif choice == "2":
            a = random.randint(2, 1000)
            b = random.randint(2, 1000)
            print(f"Сгенерированы a={a}, b={b}")
        elif choice == "3":
            while True:
                a = random.randint(2, 1000)
                b = random.randint(2, 1000)
                if is_probable_prime_fermat(a) and is_probable_prime_fermat(b):
                    break
            print(f"Сгенерированы простые a={a}, b={b}")
        else:
            raise ValueError("Неверный выбор генерации a,b")
    gcd, x, y = extended_gcd(a, b)
    return gcd, x, y, a, b

# -------------------------
# Interactive menu
# -------------------------

def main():
    while True:
        print("\nВыберите операцию:")
        print("1) Возведение в степень по модулю (y = a^x mod p)")
        print("2) Найти обратный элемент (a^-1 mod p)")
        print("3) Проверка числа на простоту (Miller–Rabin)")
        print("4) Проверка числа на простоту (Ферма)")
        print("5) Обобщённый алгоритм Евклида (НОД + x, y)")
        print("0) Выход")
        choice = input("Ваш выбор: ").strip()

        if choice == "1":
            try:
                a = int(input("Введите a: "))
                x = int(input("Введите x (может быть отрицательным): "))
                p = int(input("Введите p (модуль): "))
                res = mod_pow(a, x, p)
                print(f"Результат: {res}")
            except ValueError as e:
                print("Ошибка:", e)

        elif choice == "2":
            try:
                a = int(input("Введите a: "))
                p = int(input("Введите p (модуль): "))
                res = mod_inv(a, p)
                print(f"Обратный элемент: {res}")
            except ValueError as e:
                print("Ошибка:", e)

        elif choice == "3":
            try:
                n = int(input("Введите n: "))
                k = int(input("Введите количество итераций теста (например 5): "))
                res = is_probable_prime(n, k)
                print("Вероятно простое" if res else "Составное")
            except ValueError as e:
                print("Ошибка:", e)

        elif choice == "4":
            try:
                n = int(input("Введите n: "))
                k = int(input("Количество итераций теста Ферма (например 5): "))
                res = is_probable_prime_fermat(n, k)
                print("Вероятно простое" if res else "Составное")
            except ValueError as e:
                print("Ошибка:", e)

        elif choice == "5":
            try:
              gcd, x, y, a, b = generalized_euclid()
              print(f"НОД: {gcd}, x: {x}, y: {y}")
              print(f"Проверка: {gcd} = {a}*{x} + {b}*{y} = {a*x + b*y}")
            except ValueError as e:
              print("Ошибка:", e)

        elif choice == "0":
            print("Выход.")
            break
        else:
            print("Неверный выбор, попробуйте снова.")

if __name__ == "__main__":
    main()
