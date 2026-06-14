import hashlib
import os

# TEST BUG: Aceasta functie are o eroare intentionata (index out of range sau logic error)
# si nu reuseste sa calculeze hash-ul pentru fisiere mici.
def calculate_file_hash(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        # BUG: Daca fisierul e gol, crapa aici
        first_byte = data[0] 
        return hashlib.sha256(data).hexdigest()

def scan_directory(path):
    report = []
    for root, dirs, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            try:
                fhash = calculate_file_hash(full_path)
                report.append(f"{file}: {fhash}")
            except Exception as e:
                report.append(f"{file}: ERROR {str(e)}")
    return report

if __name__ == "__main__":
    # Creeaza niste fisiere de test, inclusiv unul gol care va cauza eroarea
    os.makedirs("test_files", exist_ok=True)
    with open("test_files/normal.txt", "w") as f: f.write("Date importante")
    with open("test_files/empty.txt", "w") as f: pass # Fisier gol (TRIGGER BUG)
    
    print("Incepem scanarea...")
    results = scan_directory("test_files")
    for r in results:
        print(r)
