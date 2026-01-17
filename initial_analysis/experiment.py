from character_mapper import CharacterMapper

def run_experiment():
    mapper = CharacterMapper()
    test_string = "Hello, BLE!"
    matrices = mapper.string_to_matrices(test_string)
    print(f"Character matrix for '{test_string}':")
    print()
    for matrix in matrices:
        for row in matrix:
            print(f"{row:08b}")  # Print each row as an 8-bit binary string
        print()

if __name__ == "__main__":
    run_experiment()