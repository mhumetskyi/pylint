# Copyright (c) 2021 Mark Byrne <mbyrnepr2@gmail.com>
# Copyright (c) 2021 Andreas Finkler <andi.finkler@gmail.com>

# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/PyCQA/pylint/blob/master/LICENSE

"""Tests for pylint.pyreverse.utils"""

from unittest.mock import patch

import astroid
import pytest

from pylint.pyreverse.utils import get_annotation, get_visibility, infer_node


@pytest.mark.parametrize(
    "names, expected",
    [
        (["__reduce_ex__", "__setattr__"], "special"),
        (["__g_", "____dsf", "__23_9"], "private"),
        (["simple"], "public"),
        (
            ["_", "__", "___", "____", "_____", "___e__", "_nextsimple", "_filter_it_"],
            "protected",
        ),
    ],
)
def test_get_visibility(names, expected):
    for name in names:
        got = get_visibility(name)
        assert got == expected, f"got {got} instead of {expected} for value {name}"


@pytest.mark.parametrize(
    "assign, label",
    [
        ("a: str = None", "Optional[str]"),
        ("a: str = 'mystr'", "str"),
        ("a: Optional[str] = 'str'", "Optional[str]"),
        ("a: Optional[str] = None", "Optional[str]"),
    ],
)
def test_get_annotation_annassign(assign, label):
    """AnnAssign"""
    node = astroid.extract_node(assign)
    got = get_annotation(node.value).name
    assert isinstance(node, astroid.AnnAssign)
    assert got == label, f"got {got} instead of {label} for value {node}"


@pytest.mark.parametrize(
    "init_method, label",
    [
        ("def __init__(self, x: str):                   self.x = x", "str"),
        ("def __init__(self, x: str = 'str'):           self.x = x", "str"),
        ("def __init__(self, x: str = None):            self.x = x", "Optional[str]"),
        ("def __init__(self, x: Optional[str]):         self.x = x", "Optional[str]"),
        ("def __init__(self, x: Optional[str] = None):  self.x = x", "Optional[str]"),
        ("def __init__(self, x: Optional[str] = 'str'): self.x = x", "Optional[str]"),
    ],
)
def test_get_annotation_assignattr(init_method, label):
    """AssignAttr"""
    assign = rf"""
        class A:
            {init_method}
    """
    node = astroid.extract_node(assign)
    instance_attrs = node.instance_attrs
    for _, assign_attrs in instance_attrs.items():
        for assign_attr in assign_attrs:
            got = get_annotation(assign_attr).name
            assert isinstance(assign_attr, astroid.AssignAttr)
            assert got == label, f"got {got} instead of {label} for value {node}"


@patch("pylint.pyreverse.utils.get_annotation")
@patch("astroid.node_classes.NodeNG.infer", side_effect=astroid.InferenceError)
def test_infer_node_1(mock_infer, mock_get_annotation):
    """Return set() when astroid.InferenceError is raised and an annotation has
    not been returned
    """
    mock_get_annotation.return_value = None
    node = astroid.extract_node("a: str = 'mystr'")
    mock_infer.return_value = "x"
    assert infer_node(node) == set()
    assert mock_infer.called


@patch("pylint.pyreverse.utils.get_annotation")
@patch("astroid.node_classes.NodeNG.infer")
def test_infer_node_2(mock_infer, mock_get_annotation):
    """Return set(node.infer()) when InferenceError is not raised and an
    annotation has not been returned
    """
    mock_get_annotation.return_value = None
    node = astroid.extract_node("a: str = 'mystr'")
    mock_infer.return_value = "x"
    assert infer_node(node) == set("x")
    assert mock_infer.called


def test_infer_node_3():
    """Return a set containing an astroid.ClassDef object when the attribute
    has a type annotation"""
    node = astroid.extract_node(
        """
        class Component:
            pass

        class Composite:
            def __init__(self, component: Component):
                self.component = component
    """
    )
    instance_attr = node.instance_attrs.get("component")[0]
    assert isinstance(infer_node(instance_attr), set)
    assert isinstance(infer_node(instance_attr).pop(), astroid.ClassDef)
