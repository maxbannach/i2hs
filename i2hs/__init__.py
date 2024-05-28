class BiMap:
    """
    A simple bidirectional map, allowing for two-way mapping between keys and values.

    Attributes:
    key_to_value (dict): A dictionary mapping keys to values.
    value_to_key (dict): A dictionary mapping values to keys.

    Methods:
    insert(key, value):
        Inserts a key-value pair into the bidirectional map.
    get_value(key):
        Retrieves the value associated with a given key.
    get_key(value):
        Retrieves the key associated with a given value.
    __str__():
        Returns a string representation of the bidirectional map.
    """
    
    def __init__(self):
        """
        Default constructor for an empty map.
        """
        self.key_to_value = {}
        self.value_to_key = {}

    def insert(self, key, value):
        """
        Insert a key-value pair into the bidirectional map.

        Parameters:
        key: The key to insert.
        value: The value to insert.
        """
        self.key_to_value[key]   = value
        self.value_to_key[value] = key

    def get_value(self, key):
        """
        Retrieve the value associated with a given key.

        Parameters:
        key: The key whose associated value is to be returned.

        Returns:
        The value associated with the given key, or None if the key is not present.
        """
        return self.key_to_value.get(key)

    def get_key(self, value):
        """
        Retrieve the key associated with a given value.

        Parameters:
        value: The value whose associated key is to be returned.

        Returns:
        The key associated with the given value, or None if the value is not present.
        """
        return self.value_to_key.get(value)

    def __str__(self):
        """
        String representation of the map for debugging.

        Returns:
        A string representing the bidirectional map.
        """
        return f'key_to_value: {self.key_to_value}\nvalue_to_key: {self.value_to_key}'

# Reimports to make the module flat.
    
from ._isinghs import Hypergraph
from ._solver  import Solver
