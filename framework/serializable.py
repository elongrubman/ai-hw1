import dataclasses
from typing import Optional

from framework.ways.streets_map import *


__all__ = ['Serializable']


class Serializable:
    def serialize(self) -> str:
        assert dataclasses.is_dataclass(self)
        def serialize_field(field: dataclasses.Field) -> str:
            field_value = getattr(self, field.name)
            if isinstance(field_value, Serializable):
                return field_value.serialize()
            if isinstance(field_value, Junction):
                return str(field_value.index)
            assert any(issubclass(field.type, primitive_type) for primitive_type in (str, int, float))
            return str(field_value)
        fields_sorted_by_name = sorted(dataclasses.fields(self), key=lambda field: field.name)
        return ','.join(serialize_field(field) for field in fields_sorted_by_name)

    @classmethod
    def deserialize(cls, serialized: str, streets_map: Optional[StreetsMap] = None):
        assert dataclasses.is_dataclass(cls)
        def deserialize_field(field: dataclasses.Field, serialized_value: str):
            if issubclass(field.type, Serializable):
                return field.type.deserialize(serialized=serialized_value, streets_map=streets_map)
            if issubclass(field.type, Junction):
                assert streets_map is not None
                return streets_map[int(serialized_value)]
            assert any(issubclass(field.type, primitive_type) for primitive_type in (str, int, float))
            return field.type(serialized_value)
        parts = serialized.split(',')
        fields_sorted_by_name = sorted(dataclasses.fields(cls), key=lambda field: field.name)
        assert len(parts) == len(fields_sorted_by_name)
        return cls(**{
            field.name: deserialize_field(field=field, serialized_value=serialized_value)
            for field, serialized_value in zip(fields_sorted_by_name, parts)
        })
