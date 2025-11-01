import random
from typing import Tuple, Optional, Dict, List
import math

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
    # write n-1 as d * 2^s
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
# Лабораторная 2: Baby-step Giant-step
# -------------------------

def baby_step_giant_step(a: int, y: int, p: int) -> Optional[int]:
    if p <= 1:
        raise ValueError("Модуль p должен быть > 1.")
    a %= p
    y %= p
    if y == 1:
        return 0
    # Проверка на взаимную простоту
    g = math.gcd(a, p)
    if g != 1:
        raise ValueError(f"Требуется gcd(a, p) = 1. Сейчас gcd({a},{p}) = {g}.")
    m = int(math.ceil(math.sqrt(p)))
    baby_steps: Dict[int,int] = {}
    aj = 1
    for j in range(m):
        if aj not in baby_steps:
            baby_steps[aj] = j
        aj = (aj * a) % p

    a_m = mod_pow(a, m, p)
    try:
        a_m_inv = mod_inv(a_m, p)
    except ValueError:
        raise ValueError("Не удалось найти обратный элемент для a^m (необратим модуль p).")

    gamma = y
    for i in range(m + 1):
        if gamma in baby_steps:
            j = baby_steps[gamma]
            x = i * m + j
            if mod_pow(a, x, p) == y:
                return x
        gamma = (gamma * a_m_inv) % p
    return None

def generate_prime_between(low: int, high: int) -> int:
    """Генерирует вероятное простое между low и high (включительно)."""
    if low >= high:
        raise ValueError("low должен быть < high")
    while True:
        candidate = random.randint(low, high)
        if candidate >= 2 and is_probable_prime(candidate, k=8):
            return candidate

def discrete_log_interactive():
    print("Решение дискретного логарифма y = a^x mod p.")
    print("Выберите вариант задания параметров:")
    print("1) Ввести a, y, p с клавиатуры")
    print("2) Сгенерировать p (простое) и a,y случайно")
    choice = input("Ваш выбор: ").strip()

    if choice == "1":
        a = int(input("Введите a: ").strip())
        y = int(input("Введите y: ").strip())
        p = int(input("Введите p (модуль): ").strip())
    elif choice == "2":
        print("Укажите диапазон для генерации простого p (рекомендуется p <= 1e9):")
        low = int(input("Нижняя граница (например 100000): ").strip())
        high = int(input("Верхняя граница (например 1000000): ").strip())
        p = generate_prime_between(low, high)
        a = random.randint(2, p-2)
        y = random.randint(1, p-1)
        print(f"Сгенерированы параметры: p={p}, a={a}, y={y}")
    else:
        print("Неверный выбор.")
        return None

    if p <= 1:
        print("Модуль p должен быть > 1.")
        return None
    if math.gcd(a, p) != 1:
        print(f"gcd(a,p) != 1 (gcd={math.gcd(a,p)}). BSGS в этой реализации ожидает взаимной простоты.")
        return None

    print("Ищу x такое, что y ≡ a^x (mod p)...")
    x = baby_step_giant_step(a, y, p)
    if x is None:
        print("Решение не найдено (в диапазоне поиска).")
    else:
        print(f"Найдено x = {x}")
    if x is not None:
        print(f"Проверка: a^x mod p = {mod_pow(a, x, p)} (ожидалось {y % p})")
    return x

# -------------------------
# Лабораторная 3: Диффи-Хеллмана
# -------------------------

def prime_factors(n: int) -> List[int]:
    """Возвращает список простых множителей n (без повторений)."""
    factors = []
    d = 2
    temp = n
    while d * d <= temp:
        if temp % d == 0:
            factors.append(d)
            while temp % d == 0:
                temp //= d
        d += 1 if d == 2 else 2
    if temp > 1:
        factors.append(temp)
    return factors

def find_primitive_root(p: int) -> Optional[int]:
    if p <= 2:
        return None
    phi = p - 1
    factors = prime_factors(phi)
    for g in range(2, p):
        ok = True
        for q in factors:
            if mod_pow(g, phi // q, p) == 1:
                ok = False
                break
        if ok:
            return g
    return None

def diffie_hellman_shared_key_interactive():
    """
    Построение общего ключа Диффи-Хеллмана.
    Доступны режимы:
    1) Ввод p, g, XA, XB с клавиатуры (g может быть не примитивным — в этом случае протокол всё равно сработает, но пространство ключей меньше).
    2) Генерация p (простое), поиск примитивного g и генерация приватных ключей XA, XB.
    Возвращает общий ключ и печатает промежуточные значения.
    """
    print("Диффи-Хеллман: выберите режим задания параметров:")
    print("1) Ввести p, g, XA, XB с клавиатуры")
    print("2) Сгенерировать p (простое), найти g (примитивный корень), сгенерировать XA, XB")
    choice = input("Ваш выбор: ").strip()

    if choice == "1":
        p = int(input("Введите p (простое предпочтительно): ").strip())
        if p <= 2:
            print("p должно быть > 2.")
            return None
        g = int(input("Введите g (основание): ").strip())
        XvA = int(input("Введите приватный ключ XA (целое, 1..p-2): ").strip())
        XvB = int(input("Введите приватный ключ XB (целое, 1..p-2): ").strip())
    elif choice == "2":
        print("Укажите диапазон для генерации простого p (например, низ=10000, верх=20000).")
        low = int(input("Нижняя граница для p: ").strip())
        high = int(input("Верхняя граница для p: ").strip())
        p = generate_prime_between(low, high)
        print(f"Сгенерировано простое p = {p}")
        g = find_primitive_root(p)
        if g is None:
            g = random.randint(2, p-2)
            print("Не найден явный примитивный корень — выбран случайный g (возможно не генератор).")
        else:
            print(f"Найден примитивный корень g = {g}")
        XvA = random.randint(2, p-2)
        XvB = random.randint(2, p-2)
        print(f"Сгенерированы приватные ключи: XA = {XvA}, XB = {XvB}")
    else:
        print("Неверный выбор.")
        return None

    if p <= 1:
        print("Модуль p должен быть > 1.")
        return None
    if not is_probable_prime(p, k=8):
        print("Внимание: p не прошёл проверку на простоту с высокой вероятностью.")

    YA = mod_pow(g, XvA, p)
    YB = mod_pow(g, XvB, p)

    print(f"Публичные ключи: YA = g^XA mod p = {YA}, YB = g^XB mod p = {YB}")

    K_A = mod_pow(YB, XvA, p)
    K_B = mod_pow(YA, XvB, p)

    if K_A != K_B:
        print("ВНИМАНИЕ: полученные ключи не совпадают! Возможно, ошибка в параметрах.")
        print(f"K_A = {K_A}, K_B = {K_B}")
        return None

    shared_key = K_A
    print(f"Общий ключ (shared key) = {shared_key}")
    return {
        "p": p,
        "g": g,
        "XvA": XvA,
        "XvB": XvB,
        "YA": YA,
        "YB": YB,
        "shared_key": shared_key
    }

# -------------------------
# Menu
# -------------------------

def main():
    while True:
        print("\nВыберите операцию:")
        print("1) Возведение в степень по модулю (y = a^x mod p)")
        print("2) Найти обратный элемент (a^-1 mod p)")
        print("3) Проверка числа на простоту (Miller–Rabin)")
        print("4) Проверка числа на простоту (Ферма)")
        print("5) Обобщённый алгоритм Евклида (НОД + x, y)")
        print("6) Дискретный логарифм (метод 'шаг младенца — шаг великана')")
        print("7) Диффи-Хеллман — построение общего ключа")
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
        
        elif choice == "6":
            try:
                discrete_log_interactive()
            except ValueError as e:
                print("Ошибка:", e)

        elif choice == "7":
            try:
                diffie_hellman_shared_key_interactive()
            except ValueError as e:
                print("Ошибка:", e)

        elif choice == "0":
            print("Выход.")
            break
        else:
            print("Неверный выбор, попробуйте снова.")

if __name__ == "__main__":
    main()
