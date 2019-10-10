from rest_framework.fields import CharField

from lib.documents.api_v1.serializers import _clone_serializer_field


def test_field_clone():
    src_field = CharField(required=False)
    dst_field = _clone_serializer_field(src_field, required=True)
    assert dst_field.required
