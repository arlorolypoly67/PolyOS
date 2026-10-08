def poly_decode(b: bytes):
    return b.decode(errors='replace').replace('�', '?')

def clamp(n, maximum, minimum):
    return max(minimum, min(n, maximum))

def chunks(data, l):
    if l <= 0:
        raise ValueError('chunk size must be positive')

    for i in range(0, len(data), l):
        yield data[i:i + l]