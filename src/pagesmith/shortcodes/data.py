"""Data lookup shortcode."""


class Data:
    """Looks up values from loaded data files.
    
    Usage:
        {% data 'site.name' %}
        {% data 'config.author.email' %}
    
    Requires: load_data_fn set via set_context()
    """

    name = 'data'

    def __init__(self):
        self.load_data_fn = None

    def set_context(self, load_data_fn):
        """Set the data loader function."""
        self.load_data_fn = load_data_fn

    def __call__(self, args=None, kwargs=None, content=None):
        path = args[0] if args else ''
        if not path or not self.load_data_fn:
            return ''
        parts = path.split('.')
        data = self.load_data_fn()
        val = data
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                return ''
        return str(val) if val is not None else ''
