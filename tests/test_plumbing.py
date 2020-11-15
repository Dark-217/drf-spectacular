import json
import sys
import typing
from datetime import datetime

import pytest
from django.conf.urls import include
from django.db import models
from django.urls import re_path
from rest_framework import generics, serializers

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import (
    detype_pattern, follow_field_source, force_instance, is_field, is_serializer, resolve_type_hint,
)
from drf_spectacular.validation import validate_schema
from tests import generate_schema


def test_is_serializer():
    assert not is_serializer(serializers.SlugField)
    assert not is_serializer(serializers.SlugField())

    assert not is_serializer(models.CharField)
    assert not is_serializer(models.CharField())

    assert is_serializer(serializers.Serializer)
    assert is_serializer(serializers.Serializer())


def test_is_field():
    assert is_field(serializers.SlugField)
    assert is_field(serializers.SlugField())

    assert not is_field(models.CharField)
    assert not is_field(models.CharField())

    assert not is_field(serializers.Serializer)
    assert not is_field(serializers.Serializer())


def test_force_instance():
    assert isinstance(force_instance(serializers.CharField), serializers.CharField)
    assert force_instance(5) == 5
    assert force_instance(dict) == dict


def test_follow_field_source_forward_reverse(no_warnings):
    class FFS1(models.Model):
        field_bool = models.BooleanField()

    class FFS2(models.Model):
        ffs1 = models.ForeignKey(FFS1, on_delete=models.PROTECT)

    class FFS3(models.Model):
        ffs2 = models.ForeignKey(FFS2, on_delete=models.PROTECT)
        field_float = models.FloatField()

    forward_field = follow_field_source(FFS3, ['ffs2', 'ffs1', 'field_bool'])
    reverse_field = follow_field_source(FFS1, ['ffs2', 'ffs3', 'field_float'])
    forward_model = follow_field_source(FFS3, ['ffs2', 'ffs1'])
    reverse_model = follow_field_source(FFS1, ['ffs2', 'ffs3'])

    assert isinstance(forward_field, models.BooleanField)
    assert isinstance(reverse_field, models.FloatField)
    assert isinstance(forward_model, models.ForeignKey)
    assert isinstance(reverse_model, models.AutoField)

    auto_schema = AutoSchema()
    assert auto_schema._map_model_field(forward_field, None)['type'] == 'boolean'
    assert auto_schema._map_model_field(reverse_field, None)['type'] == 'number'
    assert auto_schema._map_model_field(forward_model, None)['type'] == 'integer'
    assert auto_schema._map_model_field(reverse_model, None)['type'] == 'integer'


def test_detype_patterns_with_module_includes(no_warnings):
    detype_pattern(
        pattern=re_path(r'^', include('tests.test_fields'))
    )


TYPE_HINT_TEST_PARAMS = [
    (
        typing.Optional[int],
        {'type': 'integer', 'nullable': True}
    ), (
        typing.List[int],
        {'type': 'array', 'items': {'type': 'integer'}}
    ), (
        list,
        {'type': 'array', 'items': {'type': 'object', 'additionalProperties': {}}}
    ), (
        typing.Tuple[int, int, int],
        {'type': 'array', 'items': {'type': 'integer'}, 'minLength': 3, 'maxLength': 3}
    ), (
        typing.Set[datetime],
        {'type': 'array', 'items': {'type': 'string', 'format': 'date-time'}}
    ), (
        typing.FrozenSet[datetime],
        {'type': 'array', 'items': {'type': 'string', 'format': 'date-time'}}
    ), (
        typing.Dict[str, int],
        {'type': 'object', 'additionalProperties': {'type': 'integer'}}
    ), (
        typing.Dict[str, str],
        {'type': 'object', 'additionalProperties': {'type': 'string'}}
    ), (
        typing.Dict[str, typing.List[int]],
        {'type': 'object', 'additionalProperties': {'type': 'array', 'items': {'type': 'integer'}}}
    ), (
        dict,
        {'type': 'object', 'additionalProperties': {}}
    ), (
        typing.Union[int, str],
        {'oneOf': [{'type': 'integer'}, {'type': 'string'}]}
    )
]

if sys.version_info >= (3, 8):
    TYPE_HINT_TEST_PARAMS.append((
        typing.Literal['x', 'y'],
        {'enum': ['x', 'y'], 'type': 'string'}
    ))
    TYPE_HINT_TEST_PARAMS.append((
        typing.TypedDict('TD', foo=int, bar=typing.List[str]),
        {
            'type': 'object',
            'properties': {
                'foo': {'type': 'integer'},
                'bar': {'type': 'array', 'items': {'type': 'string'}}
            }
        }
    ))


@pytest.mark.parametrize(['type_hint', 'ref_schema'], TYPE_HINT_TEST_PARAMS)
def test_type_hint_extraction(no_warnings, type_hint, ref_schema):
    def func() -> type_hint:
        pass  # pragma: no cover

    # check expected resolution
    schema = resolve_type_hint(typing.get_type_hints(func).get('return'))
    assert json.dumps(schema) == json.dumps(ref_schema)

    # check schema validity
    class XSerializer(serializers.Serializer):
        x = serializers.SerializerMethodField()
    XSerializer.get_x = func

    class XView(generics.RetrieveAPIView):
        serializer_class = XSerializer

    validate_schema(generate_schema('/x', view=XView))
