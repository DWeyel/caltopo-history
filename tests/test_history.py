# SPDX-FileCopyrightText: 2026 Dennis Weyel
# SPDX-License-Identifier: AGPL-3.0-only

from app.history import diff_states, feature_type, normalize_state


def f(oid, title, geom="Point", cls=None):
    props={"title":title}
    if cls: props["class"]=cls
    geometry={"type":geom,"coordinates":[8,50] if geom=="Point" else [[8,50],[9,51]]}
    return {"type":"Feature","id":oid,"geometry":geometry,"properties":props}


def test_feature_type_inference():
    assert feature_type(f("1","A")) == "Marker"
    assert feature_type(f("2","B","LineString")) == "Shape"
    assert feature_type(f("3","C",cls="Marker")) == "Marker"


def test_diff_states():
    target={"type":"FeatureCollection","features":[f("1","old"), f("2","bring back")]}
    current={"type":"FeatureCollection","features":[f("1","new"), f("3","remove") ]}
    items=diff_states(target,current)
    assert {(x.object_id,x.status) for x in items} == {("1","change"),("2","restore"),("3","remove")}


def test_normalize_wrapped_state():
    wrapped={"timestamp":1,"state":{"type":"FeatureCollection","features":[f("1","A")]}}
    assert normalize_state(wrapped)["features"][0]["id"] == "1"
