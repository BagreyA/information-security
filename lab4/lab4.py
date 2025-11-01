import random
from math import gcd

def mod_inverse(a, m):
    """Находим обратный элемент к a по модулю m."""
    def egcd(x, y):
        if x == 0:
            return (y, 0, 1)
        g, b, d = egcd(y % x, x)
        return (g, d - (y // x) * b, b)

    g, x, _ = egcd(a, m)
    if g != 1:
        raise Exception('Обратного элемента не существует')
    return x % m

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

def generate_params():
    """Генерация параметров p, CvA, CvB, DvA, DvB."""
    while True:
        p = random.randint(2000, 5000)
        if is_prime(p):
            break

    while True:
        CvA = random.randint(2, p - 2)
        if gcd(CvA, p - 1) == 1:
            break
    DvA = mod_inverse(CvA, p - 1)

    while True:
        CvB = random.randint(2, p - 2)
        if gcd(CvB, p - 1) == 1:
            break
    DvB = mod_inverse(CvB, p - 1)

    return p, CvA, CvB, DvA, DvB

def shamir_encrypt_file(input_file, output_file, p, CvA, CvB):
    with open(input_file, "rb") as f:
        data = f.read()

    encrypted = []
    for byte in data:
        c1 = pow(byte, CvA, p)
        c2 = pow(c1, CvB, p)
        encrypted.append(c2)

    with open(output_file, "w") as f:
        f.write(" ".join(map(str, encrypted)))

def shamir_decrypt_file(input_file, output_file, p, DvA, DvB):
    with open(input_file, "r") as f:
        encrypted = list(map(int, f.read().split()))

    decrypted = []
    for c in encrypted:
        m1 = pow(c, DvB, p)
        m2 = pow(m1, DvA, p)
        decrypted.append(m2)

    with open(output_file, "wb") as f:
        f.write(bytes(decrypted))

if __name__ == "__main__":
    choice = input("Хотите ввести параметры вручную? (y/n): ").strip().lower()

    if choice == 'y':
        p = int(input("Введите p (простое число): "))
        CvA = int(input("Введите CA: "))
        CvB = int(input("Введите CB: "))
        DvA = mod_inverse(CvA, p - 1)
        DvB = mod_inverse(CvB, p - 1)
    else:
        p, CvA, CvB, DvA, DvB = generate_params()
        print(f"Сгенерированные параметры:\np={p}, CA={CvA}, CB={CvB}, DA={DvA}, DB={DvB}")

    shamir_encrypt_file("input.bin", "encrypted.txt", p, CvA, CvB)
    shamir_decrypt_file("encrypted.txt", "output.bin", p, DvA, DvB)

    print("Готово! Файл зашифрован -> encrypted.txt и расшифрован -> output.bin")
