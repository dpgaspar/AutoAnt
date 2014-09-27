
class Provider(object):
    """
        Class that keeps all classes from producers and processors
        map's them to config key.
    """

    def __init__(self):
        self._providers = list()

    def add(self, provider_type, key, provider_class, short_description):
        provider = dict()
        provider['key'] = key
        provider['provider_type'] = provider_type
        provider['class'] = provider_class
        provider['short_description'] = short_description
        self._providers.append(provider)

    def get_class(self, key):
        """
            Get class from key
        """
        for provider in self._providers:
            if provider['key'] == key:
                return provider['class']

    def get_short_description(self, cls):
        """
            Get short description from class
        """
        for provider in self._providers:
            if cls.__name__ == provider['class'].__name__:
                return provider['short_description']

    def __repr__(self):
        retstr = ''
        for provider in self._providers:
            retstr = retstr + "{0}: key:{1} - {2}\n".format(provider['provider_type'], 
                                                     provider['key'], provider['short_description'])
        return retstr

providers = Provider()


def register_producer(key, short_description):
    def inner(cls):
        providers.add('Producer', key, cls, short_description)
        return cls
    return inner


def register_processor(key, short_description):
    def inner(cls):
        providers.add('Processor', key, cls, short_description)
        return cls
    return inner
