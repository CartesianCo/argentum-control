def flip(a):
    b = 0
    print(bin(a))

    b |= (a & 0b00000001) << 3
    print(bin(b))
    b |= (a & 0b00000010) << 1
    print(bin(b))
    b |= (a & 0b00000100) >> 1
    print(bin(b))
    b |= (a & 0b00001000) >> 3
    print(bin(b))

    return b


"""
address = ((a + 1) & 0b00000001) << 3
address += ((a + 1) & 0b00000010) << 1
address += ((a + 1) & 0b00000100) >> 1
address += ((a + 1) & 0b00001000) >> 3
"""
