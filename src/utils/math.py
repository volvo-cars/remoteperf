# Copyright 2024 Volvo Cars
# SPDX-License-Identifier: Apache-2.0


class Vector(tuple):
    def __new__(cls, iterable=()):
        values = map(float, iterable)
        return super().__new__(cls, values)

    def __add__(self, other):
        if len(self) != len(other):
            raise ValueError("Vectors must be of equal lengths")
        return Vector((a + b for a, b in zip(self, other)))

    def __sub__(self, other):
        if len(self) != len(other):
            raise ValueError("Vectors must be of equal lengths")
        return Vector((a - b for a, b in zip(self, other)))

    def __mul__(self, other):
        if not isinstance(other, (float, int)):
            raise ValueError("Vector multiplication only supported with numbers")
        return Vector((a * other for a in self))

    def __truediv__(self, other):
        if not isinstance(other, (float, int)):
            raise ValueError("Vector division only supported with numbers")
        return Vector((a / other for a in self))

    def round(self, ndigits: int = 0):
        return Vector((round(n, ndigits) for n in self))

    __rmul__ = __mul__
