import random
from math import gcd
from pathlib import Path
import json
import os


def is_prime(n):
    if n < 2:
        return False
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in [2, 3, 5, 7, 11]:
        if a >= n:
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generate_prime(bits=16):
    while True:
        p = random.getrandbits(bits)
        if is_prime(p):
            return p


def modinv(a, m):
    def egcd(a, b):
        if a == 0:
            return (b, 0, 1)
        g, y, x = egcd(b % a, a)
        return (g, x - (b // a) * y, y)
    g, x, _ = egcd(a, m)
    if g != 1:
        raise Exception('Обратный элемент не существует')
    return x % m


def generate_keys(bits=16):
    p = generate_prime(bits)
    q = generate_prime(bits)
    n = p * q
    phi = (p - 1) * (q - 1)
    e = 65537
    if gcd(e, phi) != 1:
        e = random.randrange(3, phi, 2)
        while gcd(e, phi) != 1:
            e = random.randrange(3, phi, 2)
    d = modinv(e, phi)
    return {'p': p, 'q': q, 'n': n, 'e': e, 'd': d}


def save_keypair(keys):
    public = {'n': keys['n'], 'e': keys['e']}
    private = {'n': keys['n'], 'd': keys['d']}
    with open("public_key.txt", "w") as f:
        json.dump(public, f, indent=4)
    with open("private_key.txt", "w") as f:
        json.dump(private, f, indent=4)
    print("\nКлючи сохранены: public_key.txt, private_key.txt\n")


def load_key(filename):
    with open(filename, "r") as f:
        return json.load(f)


def rsa_encrypt_file(input_file, output_file, n, e):
    data = Path(input_file).read_bytes()
    encrypted = [pow(b, e, n) for b in data]
    with open(output_file, 'w') as f:
        f.write(' '.join(map(str, encrypted)))
    print(f"\nФайл зашифрован: {output_file}")
    print(f"Размер исходного: {os.path.getsize(input_file)} байт")
    print(f"Размер зашифрованного: {os.path.getsize(output_file)} байт\n")


def rsa_decrypt_file(input_file, output_file, n, d):
    with open(input_file, 'r') as f:
        encrypted = list(map(int, f.read().split()))
    decrypted = bytes([pow(c, d, n) % 256 for c in encrypted])
    Path(output_file).write_bytes(decrypted)
    print(f"\nФайл расшифрован: {output_file}")
    print(f"Размер расшифрованного файла: {os.path.getsize(output_file)} байт\n")


def main():
    print("=== RSA Шифрование/Дешифрование файлов ===")
    print("1 - ввод p, q, d вручную")
    print("2 - генерация новых ключей")
    print("3 - загрузка ключей из файла")
    mode = input("Выберите режим: ")

    keys = None

    if mode == '1':
        p = int(input("Введите простое число p: "))
        q = int(input("Введите простое число q: "))
        d = int(input("Введите закрытый ключ d: "))
        n = p * q
        phi = (p - 1) * (q - 1)
        e = modinv(d, phi)
        keys = {'p': p, 'q': q, 'n': n, 'e': e, 'd': d}
        save_keypair(keys)

    elif mode == '2':
        bits = int(input("Введите длину ключа (например 16, 32, 64): "))
        keys = generate_keys(bits)
        print(f"\nСгенерированные значения:\n"
              f"p={keys['p']}\nq={keys['q']}\nn={keys['n']}\n"
              f"e={keys['e']}\nd={keys['d']}\n")
        save_keypair(keys)

    elif mode == '3':
        print("1 - загрузить открытый ключ (public_key.txt)")
        print("2 - загрузить закрытый ключ (private_key.txt)")
        key_mode = input("Выберите тип ключа: ")

        if key_mode == '1':
            keys = load_key("public_key.txt")
            action = 'e'
        else:
            keys = load_key("private_key.txt")
            action = 'd'
    else:
        print("Неизвестный режим.")
        return

    if mode in ['1', '2']:
        action = input("Выберите действие (e - зашифровать, d - расшифровать): ").lower()

    input_file = input("Введите имя входного файла: ")
    output_file = input("Введите имя выходного файла: ")

    if action == 'e':
        rsa_encrypt_file(input_file, output_file, keys['n'], keys['e'])
    elif action == 'd':
        rsa_decrypt_file(input_file, output_file, keys['n'], keys['d'])
    else:
        print("Неизвестное действие!")


if __name__ == "__main__":
    main()
