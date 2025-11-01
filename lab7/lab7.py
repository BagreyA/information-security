import os
import secrets

# -------------------------------
# Функции для шифра Вернама
# -------------------------------

def vernam_encrypt_decrypt(input_file, output_file, key):
    """
    Функция шифрует или расшифровывает файл методом Вернама
    (XOR по байтам с ключом любой длины, ключ повторяется циклично).
    """
    with open(input_file, "rb") as f_in, open(output_file, "wb") as f_out:
        data = f_in.read()
        key_bytes = key.to_bytes((key.bit_length() + 7) // 8, byteorder='big')
        repeated_key = (key_bytes * ((len(data) // len(key_bytes)) + 1))[:len(data)]
        encrypted_data = bytes([b ^ k for b, k in zip(data, repeated_key)])
        f_out.write(encrypted_data)

# -------------------------------
# Диффи-Хеллман для генерации ключа
# -------------------------------

def diffie_hellman_key(p, g):
    a = secrets.randbelow(p-2) + 1
    b = secrets.randbelow(p-2) + 1
    A = pow(g, a, p)
    B = pow(g, b, p)
    shared_key_A = pow(B, a, p)
    shared_key_B = pow(A, b, p)
    assert shared_key_A == shared_key_B
    return shared_key_A

# -------------------------------
# Взаимодействие с пользователем
# -------------------------------

def main():
    print("=== Лабораторная работа №7: Шифр Вернама ===")
    
    action = input("Выберите действие (1 - шифровать, 2 - расшифровать): ").strip()
    if action not in ('1', '2'):
        print("Ошибка: неверный выбор действия!")
        return

    input_file = input("Введите имя исходного файла: ").strip()
    if not os.path.isfile(input_file):
        print(f"Ошибка: файл '{input_file}' не найден!")
        return

    output_file = input("Введите имя файла для результата: ").strip()

    key_choice = input("Введите ключ вручную (1) или сгенерировать автоматически (2)? ").strip()

    key_file = "key.txt"

    if key_choice == '1':
        try:
            key = int(input("Введите ключ (целое число): ").strip())
        except ValueError:
            print("Ошибка: ключ должен быть числом!")
            return
    elif key_choice == '2':
        if action == '1':
            p = 0xFFFFFFFB
            g = 5
            key = diffie_hellman_key(p, g)
            print(f"Сгенерированный ключ (Diffie-Hellman): {key}")
            with open(key_file, "w") as kf:
                kf.write(str(key))
                print(f"Ключ сохранён в файл '{key_file}'")
        else: 
            if not os.path.isfile(key_file):
                print(f"Ошибка: файл с ключом '{key_file}' не найден!")
                return
            with open(key_file, "r") as kf:
                key = int(kf.read().strip())
            print(f"Используется ключ из файла '{key_file}': {key}")
    else:
        print("Ошибка: неверный выбор генерации ключа!")
        return

    vernam_encrypt_decrypt(input_file, output_file, key)

    if action == '1':
        print(f"Файл '{input_file}' зашифрован и сохранён как '{output_file}'")
    else:
        print(f"Файл '{input_file}' расшифрован и сохранён как '{output_file}'")

if __name__ == "__main__":
    main()
