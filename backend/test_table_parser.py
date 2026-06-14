import re
chunks = ["| 1 | Ana Enache | email | Prezent |", "| 2 | Ion Pop | email | Absent |"]
for c in chunks:
    for line in c.split('\n'):
        if "|" in line and "Prezent" in line:
            cols = [x.strip() for x in line.split("|") if x.strip()]
            print(cols)
