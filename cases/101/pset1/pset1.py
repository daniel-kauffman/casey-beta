def problem_1() -> None:
    x = int(input("Choose a number between 1 and 20: "))
    y = x
    x = x * 2
    x = x + 10
    x = x // 2
    x = x - y
    print(x)  # 5


def problem_2() -> None:
    a = int(input("Choose a number: "))
    b = int(input("Choose a number: "))
    c = a + b
    d = b + c
    e = c + d
    f = d + e
    g = e + f
    h = f + g
    i = g + h
    j = h + i
    x = (a + b + c + d + e + f + g + h + i + j) // g
    print(x)  # 11


def problem_3() -> None:
    x = int(input("Choose a 4-digit number: "))
    a = x // 1000
    z = x % 10
    y = x - a * 1000 - z
    y = y + z * 1000
    y = y + a
    m = max(x, y) - min(x, y)
    y = m // 1000
    y = y + m // 100 % 10
    y = y + m // 10 % 10
    y = y + m % 10
    y = (y // 10 + y % 10)
    print(y)  # 9


def problem_4() -> None:
    x = int(input("Choose a number between 1 and 50 not divisible by 7: "))
    y = x / 7
    a = int(y * 10 % 10)
    b = int(y * 10 ** 2 % 10)
    c = int(y * 10 ** 3 % 10)
    d = int(y * 10 ** 4 % 10)
    e = int(y * 10 ** 5 % 10)
    f = int(y * 10 ** 6 % 10)
    print(int(a + b + c + d + e + f))  # 27


if __name__ == "__main__":
    problem_1()
    problem_2()
    problem_3()
    problem_4()
