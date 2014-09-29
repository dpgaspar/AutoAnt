import logging

log = logging.getLogger(__name__)


PROP_HIDDEN_PREFIX = '_prop_'


class BaseProvider(object):
    """
        Class that all processor and producers inherit from
        is responsible for setting all arguments declared with
        "register_property" decorator.
    """
    def __init__(self, **kwargs):
        self._set_properties(**kwargs)

    def _set_properties(self, **kwargs):
        for attr in dir(self):
            if PROP_HIDDEN_PREFIX in attr:
                attr_val = getattr(self, attr).get_value(**kwargs)
                attr_name = attr.replace(PROP_HIDDEN_PREFIX, '')
                setattr(self, attr_name, attr_val)


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
        provider['properties'] = list()
        self._providers.append(provider)

    def add_property(self, cls, prop):
        for provider in self._providers:
            if cls.__name__ == provider['class'].__name__:
                provider['properties'].append(prop)


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
            for prop in provider['properties']:
                retstr = retstr + " - {0}".format(prop)
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


class ProviderProperty(object):
    def __init__(self, name, description, p_type, required, default):
        self.name = name
        self.description = description
        self.p_type = p_type
        self.required = required
        self.default = default

    def get_value(self, **kwargs):
        if self.required:
            if self.name not in kwargs:
                log.critical("Required Argument is missing {0}".format(self.name))
                exit(1)
        if self.default is not None:
            try:
                return self.p_type(kwargs.get(self.name, self.default))
            except ValueError as e:
                log.critical("Cast error on property {0}:{1}".format(self.name, e))
                exit(1)
        else:
            return kwargs.get(self.name)


    def __repr__(self):
        return "({1}){0} - {2} Required={3} Default={4}\n".format(self.name,
                                                                self.p_type.__name__,
                                                                self.description,
                                                                self.required,
                                                                self.default)


def register_property(name, description, p_type, required=False, default=None):
    def inner(cls):
        prop = ProviderProperty(name, description, p_type, required, default)
        setattr(cls, PROP_HIDDEN_PREFIX + name, prop)
        setattr(cls, name, None)
        providers.add_property(cls, prop)
        return cls
    return inner
