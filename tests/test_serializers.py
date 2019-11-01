from rest_framework.fields import CharField

from documents_tools.api_v1.serializers import clone_serializer_field


def test_field_clone():
    src_field = CharField(required=False)
    dst_field = clone_serializer_field(src_field, required=True)
    assert dst_field.required
