import tkinter as tk
from tkinter import simpledialog
import random
from collections import Counter
import math

def generate_crypto_params():
    """Генерирует случайные криптографические параметры"""
    # выбираем простое число для модуля в диапазоне 5000–20000
    def next_prime(n):
        while True:
            for i in range(2, int(math.sqrt(n)) + 1):
                if n % i == 0:
                    break
            else:
                return n
            n += 1

    base = random.randint(5000, 15000)
    MOD = next_prime(base)

    SHIFT = random.randint(2, 8)   # случайный сдвиг битов
    MULT = random.randint(3, 100)  # дополнительный множитель

    # записываем параметры в файл
    with open("crypto_params.txt", "w") as f:
        f.write(f"MOD={MOD}\n")
        f.write(f"SHIFT={SHIFT}\n")
        f.write(f"MULT={MULT}\n")

    return MOD, SHIFT, MULT

def mod_inverse(a, m):
    """Поиск обратного числа (a^-1 mod m)"""
    a = a % m
    for x in range(1, m):
        if (a * x) % m == 1:
            return x
    return 1

def encrypt_card(card, key):
    """Шифрование карты с динамическими параметрами"""
    with open("crypto_params.txt", "r") as f:
        lines = f.readlines()
        MOD = int(lines[0].split("=")[1])
        SHIFT = int(lines[1].split("=")[1])
        MULT = int(lines[2].split("=")[1])

    return ((card * key * MULT) ^ (key << SHIFT)) % MOD

def decrypt_card(enc_card, key):
    """Дешифрование карты с теми же параметрами"""
    with open("crypto_params.txt", "r") as f:
        lines = f.readlines()
        MOD = int(lines[0].split("=")[1])
        SHIFT = int(lines[1].split("=")[1])
        MULT = int(lines[2].split("=")[1])

    inv = mod_inverse(key * MULT, MOD)
    val = ((enc_card ^ (key << SHIFT)) * inv) % MOD

    while val < 2:
        val += 52
    while val > 53:
        val -= 52
    return int(val)

# ==============================
# Колода и логика покера
# ==============================

suits = ['♠', '♥', '♦', '♣']
ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

def create_deck():
    deck = [i+2 for i in range(52)]
    random.shuffle(deck)
    return deck

def card_name(num):
    r = ranks[(num - 2) % 13]
    s = suits[(num - 2) // 13]
    return f"{r}{s}"

def card_rank(num):
    return (num-2)%13

def card_suit(num):
    return (num-2)//13

# ==============================
# Определение силы комбинации
# ==============================

hand_ranks = {
    "Старшая карта": 1,
    "Пара": 2,
    "Две пары": 3,
    "Тройка": 4,
    "Стрит": 5,
    "Флеш": 6,
    "Фулл хаус": 7,
    "Каре": 8,
    "Стрит Флеш": 9,
    "Роял Флеш": 10
}

def hand_strength(cards):
    ranks_only = sorted([card_rank(c) for c in cards], reverse=True)
    suits_only = [card_suit(c) for c in cards]
    counts = Counter(ranks_only)
    flush = any(suits_only.count(s) >= 5 for s in suits_only)
    sorted_ranks = sorted(set(ranks_only))
    straight = False
    for i in range(len(sorted_ranks)-4):
        if sorted_ranks[i+4] - sorted_ranks[i] == 4:
            straight = True
            break
    # проверка на Стрит Флеш
    if flush and straight:
        return "Стрит Флеш"
    if 4 in counts.values():
        return "Каре"
    if sorted(counts.values()) == [2,3]:
        return "Фулл хаус"
    if flush:
        return "Флеш"
    if straight:
        return "Стрит"
    if 3 in counts.values():
        return "Тройка"
    if list(counts.values()).count(2) == 2:
        return "Две пары"
    if 2 in counts.values():
        return "Пара"
    return "Старшая карта"

# ==============================
# GUI и логика
# ==============================

class MentalPokerApp:
    def __init__(self, master):
        self.master = master
        master.title("Ментальный покер (Техасский Холдем)")
        master.geometry("1000x600")

        self.num_players = simpledialog.askinteger(
            "Настройка", "Введите количество игроков (2-6):", minvalue=2, maxvalue=6
        )
        if not self.num_players:
            self.num_players = 2

        self.history = []

        self.main_frame = tk.Frame(master)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.players_frame = tk.Frame(self.main_frame)
        self.players_frame.pack(side="left", padx=10, pady=10)

        self.info_frame = tk.Frame(self.main_frame, bd=2, relief="sunken", padx=10, pady=10)
        self.info_frame.pack(side="right", fill="y", padx=10, pady=10)
        tk.Label(self.info_frame, text="Информация о игроке", font=("Consolas", 14, "bold")).pack()
        self.info_label = tk.Label(self.info_frame, text="", font=("Consolas", 12), justify="left")
        self.info_label.pack(pady=10)

        tk.Button(master, text="Новая раздача", command=self.new_round).pack(pady=5)
        self.output = tk.Label(master, text="", font=("Consolas", 14), justify="left")
        self.output.pack(pady=10)

        cols = (self.num_players + 1) // 2
        self.player_frames = []
        for i in range(self.num_players):
            frame = tk.Frame(self.players_frame, bd=2, relief="groove")
            row = i // cols
            col = i % cols
            frame.grid(row=row, column=col, padx=10, pady=10)

            tk.Label(frame, text=f"Игрок {i+1}").pack()
            tk.Button(frame, text="Показать карты", command=lambda i=i: self.show_player(i)).pack()
            lbl = tk.Label(frame, text="?", font=("Consolas", 16))
            lbl.pack()
            self.player_frames.append((frame, lbl))

        self.table_frame = tk.Frame(master)
        self.table_frame.pack(pady=10)

        tk.Button(master, text="Флоп", command=lambda: self.reveal_stage('flop')).pack(pady=2)
        tk.Button(master, text="Терн", command=lambda: self.reveal_stage('turn')).pack(pady=2)
        tk.Button(master, text="Ривер", command=lambda: self.reveal_stage('river')).pack(pady=2)

        self.table_labels = [tk.Label(self.table_frame, text="?", font=("Consolas", 20), width=4)
                             for _ in range(5)]
        for lbl in self.table_labels:
            lbl.pack(side="left", padx=5)

        self.new_round()

    def new_round(self):
        self.deck = create_deck()
        self.crypto_params = generate_crypto_params()
        self.keys = [random.randint(100, 999) for _ in range(self.num_players)]
        with open("player_keys.txt", "w") as f:
            for i, k in enumerate(self.keys): f.write(f"Player{i+1}={k}\n")

        deck_copy = self.deck.copy()
        self.players_enc = []
        for key in self.keys:
            hand = random.sample(deck_copy, 2)
            hand_enc = [encrypt_card(c, key) for c in hand]
            self.players_enc.append(hand_enc)
            for c in hand:
                deck_copy.remove(c)

        self.table_enc = random.sample(deck_copy, 5)

        for lbl in self.table_labels:
            lbl.config(text="?")
        for _, lbl in self.player_frames:
            lbl.config(text="?")
        self.output.config(text="Новая раздача готова!")
        self.info_label.config(text="")

        self.history.append({
            "players": [hand.copy() for hand in self.players_enc],
            "table": self.table_enc.copy()
        })

    def show_player(self, player):
        cards = [card_name(decrypt_card(c, self.keys[player])) for c in self.players_enc[player]]
        self.player_frames[player][1].config(text=", ".join(cards))
        self.info_label.config(text=f"Игрок {player+1}\nКарты: {', '.join(cards)}")

    def reveal_stage(self, stage):
        if stage == 'flop':
            for i in range(3):
                self.table_labels[i].config(text=card_name(self.table_enc[i]))
            self.output.config(text="Флоп открыт: первые 3 карты")
        elif stage == 'turn':
            self.table_labels[3].config(text=card_name(self.table_enc[3]))
            self.output.config(text="Терн открыт: 4-я карта")
        elif stage == 'river':
            self.table_labels[4].config(text=card_name(self.table_enc[4]))
            self.output.config(text="Ривер открыт: 5-я карта")
            winner, combination = self.determine_winner()
            self.output.config(
                text=f"Ривер открыт. Победитель: Игрок {winner+1} с комбинацией: {combination}"
            )

    def determine_winner(self):
        def combination_key(cards):
            ranks_only = [card_rank(c) for c in cards]
            counts = Counter(ranks_only)
            comb_type = hand_strength(cards)
            rank = hand_ranks[comb_type]

            # Создаем tiebreak по типу комбинации
            tiebreak = []

            if comb_type == "Две пары":
                pairs = sorted([r for r, cnt in counts.items() if cnt == 2], reverse=True)
                kicker = max([r for r, cnt in counts.items() if cnt == 1])
                tiebreak = pairs + [kicker]
            elif comb_type == "Пара":
                pair = max([r for r, cnt in counts.items() if cnt == 2])
                kickers = sorted([r for r, cnt in counts.items() if cnt == 1], reverse=True)
                tiebreak = [pair] + kickers
            else:
                tiebreak = sorted(ranks_only, reverse=True)

            return (rank, tiebreak)
        
        best_key = (-1, [])
        winner = 0
        best_comb = ""
        
        for i in range(self.num_players):
            player_cards = [decrypt_card(c, self.keys[i]) for c in self.players_enc[i]]
            all_cards = player_cards + [decrypt_card(c, 0) for c in self.table_enc]
            comb = hand_strength(all_cards)
            key = combination_key(all_cards)
            
            if key > best_key:
                best_key = key
                winner = i
                best_comb = comb
        
        return winner, best_comb

    def show_table(self):
        for i, lbl in enumerate(self.table_labels):
            lbl.config(text=card_name(self.table_enc[i]))
        self.output.config(text="Карты на столе открыты!")

# ==============================
# Запуск
# ==============================

root = tk.Tk()
app = MentalPokerApp(root)
root.mainloop()







# ==============================
# Простое "шифрование" для демонстрации
# ==============================

#def encrypt_card(card, key):
#    return card + key*52

#def decrypt_card(card, key):
#    return (card - 2) % 52 + 2