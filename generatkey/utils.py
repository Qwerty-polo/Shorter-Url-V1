import random
import string

def generate_key(length: int = 5) -> str:
#k=length (тобто k=5) означає: "Витягни мені 5 штук випадкових фішок з 52 букв = 10 цифр".
#choices (у множині) дозволяє повтори. Тобто може випасти "AA11b,
# результатом буде список з 5 рандомних елементів і join все обєднує"
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))