class BiMap:
    def __init__(self):
        self.key_to_value = {}
        self.value_to_key = {}

    def insert(self, key, value):
        self.key_to_value[key]   = value
        self.value_to_key[value] = key

    def get_value(self, key):
        return self.key_to_value.get(key)

    def get_key(self, value):
        return self.value_to_key.get(value)

    def __str__(self):
        return f'key_to_value: {self.key_to_value}\nvalue_to_key: {self.value_to_key}'


from ._isinghs import Hypergraph
from ._solver  import Solver
