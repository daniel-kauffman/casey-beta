with casey.group("problem_1") as _:
    for i in range(1, 21):
        _((), None, i=str(i), o="5\n")

with casey.group("problem_2") as _:
    for i in range(1, 101, 5):
        for j in range(1, 101, 7):
            _((), None, i=f"{i}\n{j}", o="11\n")

with casey.group("problem_3", w=4) as _:
    for i in range(1000, 9999, 97):
        if len(set(str(i))) == 4:
            _((), None, i=str(i), o="9\n")

with casey.group("problem_4", w=4) as _:
    for i in range(1, 50):
        if i % 7 != 0:
            _((), None, i=str(i), o="27\n")
