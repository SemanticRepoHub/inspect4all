class Calculator:
    def __init__(self, offset: int = 0):
        self.offset = offset

    def add(self, a: int, b: int) -> int:
        return a + b + self.offset


def multiply(a: int, b: int) -> int:
    return a * b
