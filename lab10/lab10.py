from Crypto.Hash import SHA256
from Crypto.Random import random
from Crypto.Util.number import getPrime, inverse
from Crypto.Util.number import isPrime
import os


def generate_parameters(bits_p=512, bits_q=160):
    while True:
        q = getPrime(bits_q)
        k = random.getrandbits(bits_p - bits_q)
        p = k * q + 1
        if is_prime(p):
            break
    while True:
        g = random.randint(2, p - 2)
        a = pow(g, (p - 1) // q, p)
        if a > 1:
            break
    return p, q, a

def is_prime(n, k=5):
    return isPrime(n)

def generate_keys(p, q, a):
    x = random.randint(1, q - 1)
    y = pow(a, x, p)
    return x, y

def sign_byte(byte, x, p, q, a):
    h = byte
    while True:
        k = random.randint(1, q - 1)
        r = pow(a, k, p) % q
        if r == 0:
            continue
        s = (k * h + x * r) % q
        if s != 0:
            break
    return r, s

def verify_byte(byte, r, s, y, p, q, a):
    h = byte
    if not (0 < r < q and 0 < s < q):
        return False
    v = inverse(h, q)
    z1 = (s * v) % q
    z2 = (-r * v) % q
    u = (pow(a, z1, p) * pow(y, z2, p)) % p % q
    return u == r

def sign_file(filename, x, p, q, a):
    with open(filename, 'rb') as f:
        data = f.read()

    h = SHA256.new(data).digest()
    signature = []

    for byte in h:
        r, s = sign_byte(byte, x, p, q, a)
        signature.append((r, s))

    return signature

def verify_file(filename, signature, y, p, q, a):
    with open(filename, 'rb') as f:
        data = f.read()

    h = SHA256.new(data).digest()
    for byte, (r, s) in zip(h, signature):
        if not verify_byte(byte, r, s, y, p, q, a):
            return False
    return True

def save_keys(x, y, p, q, a, priv_file="private.key", pub_file="public.key"):
    with open(priv_file, "w") as f:
        f.write(f"{x}\n{p}\n{q}\n{a}")
    with open(pub_file, "w") as f:
        f.write(f"{y}\n{p}\n{q}\n{a}")


def load_keys(priv_file="private.key", pub_file="public.key"):
    with open(priv_file, "r") as f:
        lines = f.read().splitlines()
        x, p, q, a = map(int, lines)

    with open(pub_file, "r") as f:
        lines = f.read().splitlines()
        y = int(lines[0])

    return x, y, p, q, a

def save_signature(signature, sig_file):
    with open(sig_file, "w") as f:
        for r, s in signature:
            f.write(f"{r},{s}\n")


def load_signature(sig_file):
    signature = []
    with open(sig_file, "r") as f:
        for line in f:
            r, s = map(int, line.strip().split(","))
            signature.append((r, s))
    return signature

def main():
    print("Электронная подпись ГОСТ Р 34.10-94 с генерацией параметров")
    action = input("1 - Генерировать новые ключи\n2 - Использовать существующие ключи\n> ")

    if action == "1":
        print("Генерация параметров ГОСТ (может занять время)...")
        p, q, a = generate_parameters(bits_p=512, bits_q=160)  # можно 1024/160 для реальной версии
        print("Параметры сгенерированы.")
        x, y = generate_keys(p, q, a)
        save_keys(x, y, p, q, a)
        print("Ключи сгенерированы и сохранены.")
    else:
        priv_file = input("Введите файл с приватным ключом: ")
        pub_file = input("Введите файл с публичным ключом: ")
        x, y, p, q, a = load_keys(priv_file, pub_file)

    task = input("1 - Подписать файл\n2 - Проверить подпись\n> ")

    if task == "1":
        filename = input("Введите имя файла для подписи: ")
        sig_file = input("Введите имя файла для сохранения подписи: ")
        signature = sign_file(filename, x, p, q, a)
        save_signature(signature, sig_file)
        print(f"Файл '{filename}' подписан. Подпись сохранена в '{sig_file}'")
    else:
        filename = input("Введите имя файла для проверки подписи: ")
        sig_file = input("Введите файл с подписью: ")
        signature = load_signature(sig_file)
        result = verify_file(filename, signature, y, p, q, a)
        print("Подпись верна!" if result else "Подпись НЕ верна!")

if __name__ == "__main__":
    main()
