import hashlib
import random
import os

# =========================
# RSA функции
# =========================
def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def modinv(a, m):
    g, x, y = extended_gcd(a, m)
    if g != 1:
        raise Exception('modular inverse does not exist')
    return x % m

def extended_gcd(a, b):
    if a == 0:
        return (b, 0, 1)
    else:
        g, y, x = extended_gcd(b % a, a)
        return (g, x - (b // a) * y, y)

def is_prime(n, k=5):
    if n <= 1:
        return False
    if n <= 3:
        return True
    d = n - 1
    r = 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def generate_prime(bits):
    while True:
        p = random.getrandbits(bits)
        p |= (1 << bits - 1) | 1
        if is_prime(p):
            return p

def generate_rsa_keys(bits=512):
    print("Генерация ключей RSA...")
    p = generate_prime(bits)
    q = generate_prime(bits)
    n = p * q
    phi = (p - 1) * (q - 1)
    e = 65537
    d = modinv(e, phi)
    print("Ключи сгенерированы!")
    return (n, e), (n, d)

# =========================
# Хеш и подпись
# =========================
def hash_file(filename):
    sha = hashlib.sha256()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha.update(block)
    return sha.digest()

def sign_file(filename, private_key, signature_file):
    n, d = private_key
    file_hash = hash_file(filename)
    signature = [pow(byte, d, n) for byte in file_hash]
    with open(signature_file, "w") as f:
        f.write(",".join(map(str, signature)))
    print(f"Файл '{filename}' подписан. Подпись сохранена в '{signature_file}'.")

def verify_file(filename, public_key, signature_file):
    n, e = public_key
    file_hash = hash_file(filename)
    with open(signature_file, "r") as f:
        signature = list(map(int, f.read().split(",")))
    if len(file_hash) != len(signature):
        return False
    for byte, sig_byte in zip(file_hash, signature):
        if pow(sig_byte, e, n) != byte:
            return False
    return True


def main():
    public_key = private_key = None

    while True:
        print("\n=== Электронная подпись RSA ===")
        print("1. Сгенерировать ключи RSA")
        print("2. Подписать файл")
        print("3. Проверить подпись файла")
        print("4. Выйти")
        choice = input("Выберите действие (1-4): ")

        if choice == "1":
            public_key, private_key = generate_rsa_keys(bits=512)
            print(f"Публичный ключ: {public_key}")
            print(f"Приватный ключ: {private_key}")

        elif choice == "2":
            if not private_key:
                print("Сначала сгенерируйте ключи (пункт 1).")
                continue
            filename = input("Введите имя файла для подписи: ")
            if not os.path.exists(filename):
                print("Файл не найден!")
                continue
            signature_file = input("Введите имя файла для подписи (например example.sig): ")
            sign_file(filename, private_key, signature_file)

        elif choice == "3":
            if not public_key:
                print("Сначала сгенерируйте ключи (пункт 1).")
                continue
            filename = input("Введите имя файла для проверки: ")
            signature_file = input("Введите имя файла с подписью: ")
            if not os.path.exists(filename) or not os.path.exists(signature_file):
                print("Файл или подпись не найдены!")
                continue
            if verify_file(filename, public_key, signature_file):
                print("Подпись верна!")
            else:
                print("Подпись НЕ верна!")

        elif choice == "4":
            print("Выход из программы.")
            break

        else:
            print("Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main()
