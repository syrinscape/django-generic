import unittest

from generic.utils.inheritance import get_subclasses


class ModelMeta(object):
    def __init__(self, abstract):
        self.abstract = abstract


class BaseModel(object):
    _meta = ModelMeta(abstract=False)


class ConcreteModel(BaseModel):
    _meta = ModelMeta(abstract=False)


class AbstractModel(BaseModel):
    _meta = ModelMeta(abstract=True)


class ConcreteLeafModel(AbstractModel):
    _meta = ModelMeta(abstract=False)


class InheritanceTests(unittest.TestCase):
    def test_get_subclasses_recurses_and_filters_abstract_models(self):
        self.assertEqual(
            set(get_subclasses(BaseModel)),
            {BaseModel, ConcreteModel, ConcreteLeafModel},
        )
        self.assertEqual(
            set(get_subclasses(BaseModel, include_abstract=True)),
            {BaseModel, ConcreteModel, AbstractModel, ConcreteLeafModel},
        )
