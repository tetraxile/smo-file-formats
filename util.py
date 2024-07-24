import enum
import struct
import sys
import typing


class Log:
    @staticmethod
    def error(message: str) -> typing.NoReturn:
        print(f"error: {message}", file=sys.stderr)
        sys.exit(1)

    @staticmethod
    def info(message: str):
        print(f"info: {message}")


class ByteOrder(enum.Enum):
    little = "<"
    big = ">"


class BinaryReader:
    def __init__(self, stream: bytes, byte_order: ByteOrder = ByteOrder.little):
        self.stream = stream
        self.byte_order = byte_order
        self._position = 0

    @property
    def position(self) -> int:
        return self._position
    
    def seek(self, offset: int, *, relative: bool = False):
        if relative:
            self._position += offset
        else:
            self._position = offset

    @staticmethod
    def _check_len(buffer: bytes, size: int):
        if len(buffer) != size:
            raise OSError("EOF reached")
    
    def read(self, size: int = -1, suppress: bool = False) -> bytes:
        if size == -1:
            out = self.stream[self._position:]
            self._position += len(out)
            return out
        
        out = self.stream[self._position:self._position+size]
        self._position += size
        
        if not suppress:
            self._check_len(out, size)
        return out
    
    def _read(self, size: int, fmt: str, type_: type) -> typing.Any:
        out = self.read(size)
        endianness = self.byte_order.value
        return type_(*struct.unpack(endianness + fmt, out))

    def peek(self, size: int = 1) -> bytes:
        offset = self.position
        out = self.read(size)
        self.seek(offset)
        return out
    
    def read_bool(self) -> bool:
        out = self.read(1)
        if out == b'\x00':
            return False
        else:
            return True
        
    def read_i8(self) -> int:
        return self._read(1, "b", int)

    def read_u8(self) -> int:
        return self._read(1, "B", int)
        
    def read_i16(self) -> int:
        return self._read(2, "h", int)

    def read_u16(self) -> int:
        return self._read(2, "H", int)
    
    def read_u24(self) -> int:
        out = self.read(3)
        if self.byte_order == ByteOrder.little:
            return struct.unpack("<I", out + b'\x00')[0]
        else:
            return struct.unpack(">I", b'\x00' + out)[0]
        
    def read_i32(self) -> int:
        return self._read(4, "i", int)

    def read_u32(self) -> int:
        return self._read(4, "I", int)
        
    def read_i64(self) -> int:
        return self._read(8, "q", int)

    def read_u64(self) -> int:
        return self._read(8, "Q", int)
        
    def read_bytes(self, size: int) -> bytes:
        return self.read(size)
    
    def read_f16(self) -> float:
        return self._read(2, "s", int)
        
    def read_f32(self) -> float:
        return self._read(4, "f", int)
    
    def read_f64(self) -> float:
        return self._read(8, "d", int)
    
    def read_bools(self, count: int) -> list[bool]:
        return [self.read_bool() for _ in range(count)]
        
    def read_i8s(self, count: int) -> list[int]:
        return [self.read_i8() for _ in range(count)]

    def read_u8s(self, count: int) -> list[int]:
        return [self.read_u8() for _ in range(count)]
        
    def read_i16s(self, count: int) -> list[int]:
        return [self.read_i16() for _ in range(count)]

    def read_u16s(self, count: int) -> list[int]:
        return [self.read_u16() for _ in range(count)]
        
    def read_i32s(self, count: int) -> list[int]:
        return [self.read_i32() for _ in range(count)]

    def read_u32s(self, count: int) -> list[int]:
        return [self.read_u32() for _ in range(count)]
        
    def read_i64s(self, count: int) -> list[int]:
        return [self.read_i64() for _ in range(count)]

    def read_u64s(self, count: int) -> list[int]:
        return [self.read_u64() for _ in range(count)]

    def read_f16s(self, count: int) -> list[float]:
        return [self.read_f16() for _ in range(count)]

    def read_f32s(self, count: int) -> list[float]:
        return [self.read_f32() for _ in range(count)]

    def read_f64s(self, count: int) -> list[float]:
        return [self.read_f64() for _ in range(count)]

        
    def read_string(self, encoding_name: str, size: int = -1, char_size: int = 1) -> str:
        if size == -1:
            out = b""
            while (char := self.read(char_size)) != b'\x00':
                out += char
        else:
            out = self.read(size, suppress=True)
            # cut string off early at null terminator
            chars = [out[i:i+char_size] for i in range(0, size, char_size)]
            for i, char in enumerate(chars):
                if not int.from_bytes(char, self.byte_order.name):
                    out = out[:i]
        
        return out.decode(encoding_name)
    
    def read_signature(self, size: int, expected: str) -> str:
        signature = self.read_string("ascii", size)
        if signature != expected:
            Log.error(f"file signature was {signature}, expected {expected}")
        
        return signature
    
    def read_byte_order(self) -> ByteOrder:
        byte_order = self.read_bytes(2)

        if byte_order == b'\xFE\xFF':
            self.byte_order = ByteOrder.big
        elif byte_order == b'\xFF\xFE':
            self.byte_order = ByteOrder.little
        else:
            Log.error("invalid byte order")
        
        return self.byte_order
    
    def align(self, alignment: int):
        pos = self.position
        delta = (-pos % alignment + alignment) % alignment
        self.seek(delta, relative=True)
