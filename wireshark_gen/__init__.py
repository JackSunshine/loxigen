# Copyright 2013, Big Switch Networks, Inc.
#
# LoxiGen is licensed under the Eclipse Public License, version 1.0 (EPL), with
# the following special exception:
#
# LOXI Exception
#
# As a special exception to the terms of the EPL, you may distribute libraries
# generated by LoxiGen (LoxiGen Libraries) under the terms of your choice, provided
# that copyright and licensing notices generated by LoxiGen are not altered or removed
# from the LoxiGen Libraries and the notice provided below is (i) included in
# the LoxiGen Libraries, if distributed in source code form and (ii) included in any
# documentation for the LoxiGen Libraries, if distributed in binary form.
#
# Notice: "Copyright 2013, Big Switch Networks, Inc. This library was generated by the LoxiGen Compiler."
#
# You may not use this file except in compliance with the EPL or LOXI Exception. You may obtain
# a copy of the EPL at:
#
# http://www.eclipse.org/legal/epl-v10.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# EPL for the specific language governing permissions and limitations
# under the EPL.

import os
from collections import namedtuple
import loxi_utils.loxi_utils as utils
import loxi_front_end
import loxi_globals
from loxi_ir import *
import field_info
import template_utils

templates_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')

DissectorField = namedtuple("DissectorField", ["fullname", "name", "type", "base", "enum_table"])

proto_names = { 1: 'of10', 2: 'of11', 3: 'of12', 4: 'of13' }
def make_field_name(version, ofclass_name, member_name):
    return "%s.%s.%s" % (proto_names[version.wire_version],
                         ofclass_name[3:],
                         member_name)

def get_reader(version, cls, m):
    """
    Decide on a reader function to use for the given field
    """
    ofproto = loxi_globals.ir[version]
    enum = ofproto.enum_by_name(m.oftype)
    if enum and 'wire_type' in enum.params:
        return "read_" + enum.params['wire_type']
    else:
        return "read_" + m.oftype.replace(')', '').replace('(', '_')

def get_peeker(version, cls, m):
    """
    Decide on a peeker function to use for the given field
    """
    ofproto = loxi_globals.ir[version]
    enum = ofproto.enum_by_name(m.oftype)
    if enum and 'wire_type' in enum.params:
        return "peek_" + enum.params['wire_type']
    else:
        return "peek_" + m.oftype.replace(')', '').replace('(', '_')

def get_field_info(version, cls, name, oftype):
    """
    Decide on a Wireshark type and base for a given field.

    Returns (type, base)
    """
    if oftype.startswith("list"):
        return "bytes", "NONE", "nil"

    ofproto = loxi_globals.ir[version]

    enum = ofproto.enum_by_name(oftype)
    if not enum and (cls, name) in field_info.class_field_to_enum:
        enum_name = field_info.class_field_to_enum[(cls, name)]
        enum = ofproto.enum_by_name(enum_name)

    if enum:
        field_type = "uint32"
    elif oftype in field_info.oftype_to_wireshark_type:
        field_type = field_info.oftype_to_wireshark_type[oftype]
    else:
        print "WARN missing oftype_to_wireshark_type for", oftype
        field_type = "bytes"

    if enum:
        if enum.is_bitmask:
            field_base = "HEX"
        else:
            field_base = "DEC"
    elif oftype in field_info.field_to_base:
        field_base = field_info.field_to_base[name]
    elif oftype in field_info.oftype_to_base:
        field_base = field_info.oftype_to_base[oftype]
    else:
        print "WARN missing oftype_to_base for", oftype
        field_base = "NONE"

    if enum:
        enum_table = 'enum_v%d_%s' % (version.wire_version, enum.name)
    else:
        enum_table = 'nil'

    return field_type, field_base, enum_table

def create_fields():
    r = []
    for version, ofproto in loxi_globals.ir.items():
        for ofclass in ofproto.classes:
            for m in ofclass.members:
                if isinstance(m, OFPadMember):
                    continue
                fullname = make_field_name(version, ofclass.name, m.name)
                field_type, field_base, enum_table = get_field_info(version, ofclass.name, m.name, m.oftype)
                r.append(DissectorField(fullname, m.name, field_type, field_base, enum_table))

    return r

def generate(install_dir):
    context = {
        'fields': create_fields(),
    }

    with template_utils.open_output(install_dir, 'wireshark/openflow.lua') as out:
        template_utils.render_template(out, "openflow.lua", [templates_dir], context)
