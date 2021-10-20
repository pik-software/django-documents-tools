import re
from collections import OrderedDict

from djangorestframework_camel_case.util import camelize_re
from djangorestframework_camel_case.util import underscore_to_camel


class FixDocumentFieldsCamelcaseMixin:
    DOCUMENT_FIELD = 'document_fields'

    @staticmethod
    def _camelize(data):
        if isinstance(data, str):
            data = re.sub(camelize_re, underscore_to_camel, data)
        return data

    def camelization_hook(self, data):
        """
        >>> d = FixDocumentFieldsCamelcaseMixin()

        >>> d.camelization_hook( \
            data={'document_fields':['abc_xyz', 'qwe_rty']})
        OrderedDict([('document_fields', ['abcXyz', 'qweRty'])])

        >>> d.camelization_hook( \
            data={'document_fields':['abc_xyz'], 'f': ['asd_zxc']})
        OrderedDict([('document_fields', ['abcXyz']), ('f', ['asd_zxc'])])
        """

        if isinstance(data, dict):
            new_dict = OrderedDict()
            for key, value in data.items():
                new_key = key
                new_value = self.camelization_hook(value)
                if key == self.DOCUMENT_FIELD and isinstance(value, list):
                    new_value = [self._camelize(elem) for elem in value]
                new_dict[new_key] = new_value
            return new_dict

        if isinstance(data, list):
            new_list = [self.camelization_hook(elem) for elem in data]
            return new_list
        return data
