#!/usr/bin/env python

columns = 2
primitives = 8
addresses = 13
column_grouping = columns * addresses

address_to_index_even = (0, 10, 7, 4, 1, 11, 8, 5, 2, 12, 9, 6, 3)
address_to_index_odd = (9, 6, 3, 0, 10, 7, 4, 1, 11, 8, 5, 2, 12) # Rotated 3

index_to_address_even = (0, 4, 8, 12, 3, 7, 11, 2, 6, 10, 1, 5, 9)
index_to_address_odd = (3, 7, 11, 2, 6, 10, 1, 5, 9, 0, 4, 8, 12) # Rotated 4

def column_from_nozzle(nozzle):
    return nozzle % columns

def column_from_primitive(primitive):
    return primitive % columns

def primitive_from_nozzle(nozzle):
    return int(nozzle / column_grouping) * columns + column_from_nozzle(nozzle)

def index_from_nozzle(nozzle):
    return int(int(nozzle % column_grouping) / columns)

def index_from_primitive_address(primitive, address):
    return ((address * 10) + (column_from_primitive(primitive) * 9)) % addresses

def address_from_nozzle(nozzle):
    return ((nozzle * columns) + column_from_nozzle(nozzle)) % addresses

def address_from_primitive_index(primitive, index):
    return (index * 4 + column_from_primitive(primitive) * 3) % addresses

def nozzle_from_primitive_index(primitive, index):
    return int(primitive / 2) * column_grouping + 2 * index + column_from_primitive(primitive)

def nozzle_from_primitive_address(primitive, address):
    index = index_from_primitive_address(primitive, address)

    return nozzle_from_primitive_index(primitive, index)

def offset_for_nozzle(nozzle):
    primitive = primitive_from_nozzle(nozzle)
    index = index_from_nozzle(nozzle)

    primitive_offset_x, primitive_offset_y = offset_for_primitive(primitive)
    index_offset_x, index_offset_y = offset_for_index(index)

    x_offset = primitive_offset_x + index_offset_x
    y_offset = primitive_offset_y + index_offset_y

    return (x_offset + 12, y_offset)

def offset_for_primitive(primitive):
    if primitive % 2:
        x_offset = -12
    else:
        x_offset = 0

    y_offset = (int(primitive / 2) * column_grouping) + (primitive % 2)

    return (x_offset, y_offset*2)

def offset_for_index(index):
    return (0, index * 4)
