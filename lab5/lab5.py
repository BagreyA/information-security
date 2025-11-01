import struct
import sys
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util import number
from Crypto.Util.number import bytes_to_long, long_to_bytes, inverse

MAGIC = b'ELGAMALHY'

def generate_elgamal_params(key_size_bits=2048):
    """
    Генерирует параметры ElGamal:
    p — большое простое число
    g — генератор
    x — приватный ключ (DvB)
    y — публичный ключ (CvB) = g^x mod p
    """
    p = number.getStrongPrime(key_size_bits)
    g = number.getRandomRange(2, p-1)
    x = number.getRandomRange(2, p-2)
    y = pow(g, x, p)
    return p, g, y, x

def elgamal_encrypt_int(m_int, p, g, y):
    """
    Шифрование числа m_int (0 <= m < p).
    Возвращает пару (c1, c2).
    """
    if not (0 <= m_int < p):
        raise ValueError("m_int должно удовлетворять 0 <= m < p")
    k = number.getRandomRange(2, p-2)
    c1 = pow(g, k, p) 
    s = pow(y, k, p)
    c2 = (m_int * s) % p 
    return c1, c2

def elgamal_decrypt_int(c1, c2, p, x):
    """
    Расшифровка числа с помощью приватного ключа x.
    m = c2 * (c1^x)^(-1) mod p
    """
    s = pow(c1, x, p)
    s_inv = inverse(s, p)
    m = (c2 * s_inv) % p
    return m

def int_to_bytes_with_min_len(n):
    """Конвертирует число в байты (минимум 1 байт)."""
    b = long_to_bytes(n)
    return b if b else b'\x00'

def pack_length_prefixed_int(n):
    """Кодирует число: [4 байта длина][байты числа]."""
    b = int_to_bytes_with_min_len(n)
    return struct.pack('>I', len(b)) + b

def unpack_length_prefixed_int(f):
    """Считывает число в формате [4 байта длина][байты]."""
    raw = f.read(4)
    if len(raw) < 4:
        raise EOFError("Неожиданный конец файла при чтении длины")
    (l,) = struct.unpack('>I', raw)
    b = f.read(l)
    if len(b) < l:
        raise EOFError("Неожиданный конец файла при чтении числа")
    return bytes_to_long(b)

# -----------------------------------------
# Основные функции: шифрование и расшифровка файла
# -----------------------------------------
def encrypt_file(input_path, output_path, p=None, g=None, y=None, key_size_bits=2048):
    """
    Шифрует файл.
    - Если p,g,y заданы, они используются.
    - Если не заданы, генерируются новые параметры ElGamal (p,g,x,y).
    Возвращает:
        (x, p, g, y) если ключи сгенерированы,
        (None, p, g, y) если ключи были переданы вручную.
    """
    if p is None or g is None or y is None:
        p, g, y, x = generate_elgamal_params(key_size_bits)
        generated = True
    else:
        x = None
        generated = False

    with open(input_path, 'rb') as fin:
        plaintext = fin.read()

    aes_key = get_random_bytes(32)

    cipher = AES.new(aes_key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    nonce = cipher.nonce

    m_int = bytes_to_long(aes_key)

    if m_int >= p:
        if generated:
            new_bits = max(key_size_bits, m_int.bit_length() + 64)
            p, g, y, x = generate_elgamal_params(new_bits)
        else:
            raise ValueError("Заданный p слишком мал для хранения AES ключа.")

    c1, c2 = elgamal_encrypt_int(m_int, p, g, y)

    with open(output_path, 'wb') as fout:
        fout.write(MAGIC)                      
        fout.write(pack_length_prefixed_int(p))
        fout.write(pack_length_prefixed_int(g))
        
        fout.write(pack_length_prefixed_int(c1))
        fout.write(pack_length_prefixed_int(c2))
        fout.write(struct.pack('B', len(nonce)))
        fout.write(nonce)
        fout.write(struct.pack('B', len(tag)))
        fout.write(tag)
        fout.write(ciphertext)

    if generated:
        return x, p, g, y
    else:
        return None, p, g, y

def decrypt_file(input_path, output_path, x):
    """
    Расшифровывает файл:
    - Читает контейнер,
    - Достаёт p,g,c1,c2,nonce,tag,шифртекст,
    - Восстанавливает AES-ключ через ElGamal,
    - Расшифровывает файл AES-GCM.
    """
    with open(input_path, 'rb') as fin:
        magic = fin.read(len(MAGIC))
        if magic != MAGIC:
            raise ValueError("Формат файла не поддерживается (magic mismatch)")
        p = unpack_length_prefixed_int(fin)
        g = unpack_length_prefixed_int(fin)
        c1 = unpack_length_prefixed_int(fin)
        c2 = unpack_length_prefixed_int(fin)
        (nlen,) = struct.unpack('B', fin.read(1))
        nonce = fin.read(nlen)
        (tlen,) = struct.unpack('B', fin.read(1))
        tag = fin.read(tlen)
        ciphertext = fin.read()

    m_int = elgamal_decrypt_int(c1, c2, p, x)
    aes_key = long_to_bytes(m_int)

    if len(aes_key) < 32:
        aes_key = (b'\x00' * (32 - len(aes_key))) + aes_key
    elif len(aes_key) > 32:
        aes_key = aes_key[-32:]

    cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)

    with open(output_path, 'wb') as fout:
        fout.write(plaintext)

    return True

def prompt_int(prompt_text):
    """Запрашивает целое число у пользователя."""
    s = input(prompt_text).strip()
    return int(s)

def main():
    print("ElGamal Hybrid File Encryptor/Decryptor")
    print("1) Шифрование файла")
    print("2) Расшифровка файла")
    choice = input("Выберите 1 или 2: ").strip()

    if choice == '1':
        inpath = input("Введите путь к исходному файлу: ").strip()
        outpath = input("Введите путь для зашифрованного файла: ").strip()
        mode = input("Ввести вручную p,g,y? (y/N): ").strip().lower()

        if mode == 'y':
            # Пользователь вводит свои параметры
            print("Введите p, g, y (CvB) в десятичном виде:")
            p = prompt_int("p = ")
            g = prompt_int("g = ")
            y = prompt_int("y (CvB) = ")
            _, p, g, y = encrypt_file(inpath, outpath, p=p, g=g, y=y)
            print("Файл зашифрован с заданными параметрами (p,g,y).")
        else:
            # Генерируем новые параметры
            bits = int(input("Размер простого p в битах [2048]: ").strip() or "2048")
            x, p, g, y = encrypt_file(inpath, outpath, key_size_bits=bits)
            print("Файл зашифрован и сохранён в:", outpath)
            print("Сгенерированы ключи:")
            print("p (бит) =", p.bit_length())
            print("p =", p)
            print("g =", g)
            print("CvB (y) =", y)
            print("DvB (x, приватный ключ) =", x)
            print("!!! Сохраните x в надёжном месте для расшифровки !!!")

    elif choice == '2':
        inpath = input("Введите путь к зашифрованному файлу: ").strip()
        outpath = input("Введите путь для расшифрованного файла: ").strip()
        print("Введите приватный ключ DvB (x):")
        x = prompt_int("x = ")
        decrypt_file(inpath, outpath, x)
        print("Файл успешно расшифрован:", outpath)

    else:
        print("Неверный выбор. Выход.")
        sys.exit(1)

if __name__ == '__main__':
    main()
