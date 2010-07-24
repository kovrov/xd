from xml.etree.ElementTree import ElementTree, tostring

indent = 1


# "typeinfo" objects are initialized with an xml subtree, to produce code by calling `print_src()` method.

class PrimitiveInfo:
	def __init__(self, name):
		self.name = name
	def fixed(self):
		#print "#"+' '*indent+"PrimitiveInfo(%s).fixed -> True" % self.name
		return True

class EnumInfo:
	def __init__(self, element):
		self.name = element.attrib['name'].upper()
		self.members = []
		self.xml = tostring(element).strip()
		self.type = None
		for i in element:
			if len(i) == 0:
				init = None;
			elif i[0].tag == 'value':
				init = i[0].text
			elif i[0].tag == 'bit':
				init = "1 << " + i[0].text
			else:
				assert False
			self.members.append([tr_name(i.attrib['name']), init])
	def fixed(self):
		#print "#"+' '*indent+"EnumInfo(%s).fixed -> True" % self.name
		return True
	def print_src(self):
		print "enum", self.name
		print "{"
		for member in self.members:
			if member[1] is not None:
				print "   ", member[0], "=", member[1] + ","
			else:
				print "   ", member[0] + ","
		print "}"

class TypedefInfo:
	def __init__(self, element):
		if element.tag == 'typedef':
			self.name = tr(element.attrib['newname'])
			self.type = tr(element.attrib['oldname'])
		else:
			self.name = tr(element.attrib['name'])
			self.type = "uint"
		self.xml = tostring(element).strip()
	def fixed(self):
		#print "#"+' '*indent+"TypedefInfo(%s).fixed -> %s" % (self.name, type_registry[self.type].fixed())
		return type_registry[self.type].fixed()
	def print_src(self):
		print "typedef %s %s;" % (self.type, self.name)


class FieldMember:
	def __init__(self, element, ctx):
		self.name = tr_name(element.attrib['name'])
		self.type = tr(element.attrib['type'])
		self.enum = element.attrib.get('enum')
		self.mask = element.attrib.get('mask')
		assert 0 == len(element)
	def fixed(self):
		#print "#"+' '*indent+"FieldMember(%s).fixed -> %s" % (self.name, type_registry[self.type].fixed())
		return type_registry[self.type].fixed()
	def declarations(self, ctx_members=[]):
		return ((self.type, self.name),)

class PadMember(object):
	def __init__(self, element, ctx):
		count = ctx.get('pad_count', 0)
		self.name = "_pad" + str(count)
		ctx['pad_count'] = count + 1
		self.type = "byte[%s]" % element.attrib['bytes']
		assert 0 == len(element)
		assert 1 == len(element.attrib)
	def fixed(self):
		#print "#"+' '*indent+"PadMember(%s).fixed -> True" % self.name
		return True
	def declarations(self, ctx_members=[]):
		return ((self.type, self.name),)


class ListMember(object):
	def __init__(self, element, ctx):
		self.element = element
		self.name = tr_name(element.attrib['name'])
		self.element_type = tr(element.attrib['type'])
		self.type = self.element_type + ("[%s]" % self.length_expr() if self.length_expr().isdigit() else "[]")
	def fixed(self):
		#print "#"+' '*indent+"ListMember(%s).fixed -> %s" % (self.name, self.length_expr.isdigit())
		return self.length_expr().isdigit()
	def declarations(self, ctx_members=[]):
		#print "    " * idt + tr('CARD32') + "[%s] values;" % self.type
		return ((self.type, self.name),)
	def to_iovec(self, idt, ctx_name, part_idx, is_request):
		print
		if self.length_expr(ctx_name):
			# FIXME: context pointer for length_expr (?)
			print "    " * idt + "assert (%s == %s.%s.length);" % (self.length_expr(ctx_name), ctx_name,self.name)
		print "    " * idt + "parts[%d].iov_base = %s.%s.ptr;" % (part_idx, ctx_name,self.name)
		print "    " * idt + "parts[%d].iov_len = %s.%s.length * %s.sizeof;" % (part_idx, ctx_name,self.name, self.element_type)
		if is_request:
			print "    " * idt + "this.length += parts[%d].iov_len;" % part_idx
		part_idx += 1
		print
		print "    " * idt + "parts[%d].iov_base = pad.ptr;" % part_idx
		print "    " * idt + "parts[%d].iov_len = pad4(%s.%s.length * %s.sizeof);" % (part_idx, ctx_name,self.name, self.element_type)
		return part_idx + 1
	def offsetof_name(self):
		return self.name
	def length_expr(self, ctx_name='this'):
		# TODO: refactor to merge with ExprFieldMember.value_expr.flatten
		def flatten(em):
			if em.tag == 'op':
				a,b = em
				return '(' + " ".join((flatten(a), em.attrib['op'], flatten(b))) + ')'
			if em.tag == 'fieldref':
				assert 0 == len(em)
				assert 0 == len(em.attrib)
				# TODO: consider to check if member really in ctx_members:
				return '.'.join((ctx_name, em.text))
			# em.tag == 'value'
			assert 0 == len(em)
			assert 0 == len(em.attrib)
			return em.text
		# element[0] is exprfield?
		return flatten(self.element[0]) if len(self.element) == 1 else ""


class ValueParamMember(object):
	def __init__(self, element, ctx):
		self.mask_type = tr(element.attrib['value-mask-type'])
		self.mask_name = tr_name(element.attrib['value-mask-name'])
		self.list_name = tr_name(element.attrib['value-list-name'])
	def fixed(self):
		#print "#"+' '*indent+"ListMember(%s).fixed -> %s" % (self.name, self.length_expr.isdigit())
		return False
	def declarations(self, ctx_members=[]):
		res = []
		# HACK: checking against ctx_members as a specal case for ConfigureWindow
		# request, allowing padding of value_mask (mask_name)
		for m in ctx_members:
			if type(m) != ValueParamMember and m.name == self.mask_name:
				break
		else:
			res.append((self.mask_type, self.mask_name))
		res.append((tr('CARD32')+"[]", self.list_name))
		return res
	def to_iovec(self, idt, ctx_name, part_idx, is_request):
		print
		print "    " * idt + "parts[%d].iov_base = %s.%s.ptr;" % (part_idx, ctx_name,self.list_name)
		print "    " * idt + "parts[%d].iov_len = bitcount(%s.%s) * %s.sizeof;" % (part_idx, ctx_name,self.mask_name, tr('CARD32'))
		if is_request:
			print "    " * idt + "this.length += parts[%d].iov_len;" % part_idx
		return part_idx + 1
	def offsetof_name(self):
		return self.list_name
'''
uint mask;
uint[] values;
foreach (key; opt.keys.sort)
{
	mask |= key;
	values ~= opt[key];
}
'''

class ExprFieldMember(object):
	def __init__(self, element, ctx):
		self.name = tr_name(element.attrib['name'])
		self.type = tr(element.attrib['type'])
		self.element = element
	def declarations(self, ctx_members=[]):
		return ((self.type, self.name),)
	def value_expr(self, ctx_members, ctx_name='this'):
		# see xcbgen.expr.Expression
		def flatten(em):
			if em.tag == 'op':
				a,b = em
				return '(' + " ".join((flatten(a), em.attrib['op'], flatten(b))) + ')'
			if em.tag == 'fieldref':
				assert 0 == len(em)
				assert 0 == len(em.attrib)
				for member in ctx_members:
					if member.name == em.text:
						return '.'.join((ctx_name, em.text))
				# it is not a datamember, assuming this is a length
				assert em.text.endswith('_len'), em.text
				return '.'.join((ctx_name, em.text.rsplit('_', 1)[0] + '.length'))
			# em.tag == 'value'
			assert 0 == len(em)
			assert 0 == len(em.attrib)
			return em.text
		assert len(self.element) == 1
		return flatten(self.element[0])


class StructInfo(object):
	def __init__(self, element, ctx=None):
		self.type = 'struct'
		self.is_request = element.tag == 'request'
		self.is_reply = element.tag == 'reply'
		# FIXME: standard fields - reply
		self.name = 'Reply' if element.tag == 'reply' else tr(element.attrib['name'])
		self.opcode = element.attrib['opcode'] if self.is_request else None
		self.members = []
		self.reply_struct = None
		self.xml = tostring(element).strip()
		ctx = {'structinfo': self} # just in case...
		for i in element:
			member = { 'field':FieldMember,
			           'pad':PadMember,
			           'list':ListMember,
			           'valueparam':ValueParamMember,
			           'reply':StructInfo,
			           'exprfield':ExprFieldMember }[i.tag](i, ctx)
			if type(member) is StructInfo:
				self.reply_struct = member
			else:
				self.members.append(member)

	def fixed(self):
		global indent
		#print "#"+' '*indent+"StructInfo(%s).fixed ..." % self.name
		indent += 1
		for member in self.members:
			if not member.fixed():
				indent -= 1
				#print "#"+' '*indent+"... False"
				return False
		indent -= 1
		#print "#"+' '*indent+"... True"
		return True
	def print_src(self, idt=0, from_bytes=False, to_iovec=False):
		print
		print "    " * idt + "struct", self.name
		print "    " * idt + "{"
		idt += 1

		# data member declarations
		first_member = ("byte[1]", "_pad0") if len(self.members) == 0 else self.members[0].declarations(self.members)[0]
		rest_members = [] if len(self.members) == 0 else self.members[1:]
		if self.is_request:  # FIXME: does to_iovec means request? NO!!!
			# standard request fields
			print "    " * idt + "ubyte opcode = %s;" % self.opcode  # major opcode
			print "    " * idt + first_member[0], first_member[1] + ";"
			print "    " * idt + "ushort length;  // request length expressed in units of four bytes"
			for t, n in [d for m in rest_members for d in m.declarations(self.members)]:
				print "    " * idt + t, n + ";"
		elif self.is_reply:
			print "    " * idt + "ubyte response_type;"
			print "    " * idt + first_member[0], first_member[1] + ";"
			print "    " * idt + "ushort sequence;"
			print "    " * idt + "uint length;  // repy length expressed in units of four bytes"
			for t, n in [d for m in rest_members for d in m.declarations(self.members)]:
				print "    " * idt + t, n + ";"
		else:
			for t, n in [d for m in self.members for d in m.declarations(self.members)]:
				print "    " * idt + t, n + ";"
					
		# nested struct declaration
		if self.reply_struct:
			self.reply_struct.print_src(idt=idt, from_bytes=True)

		if from_bytes:
			def nested_from_bytes(ctx_name, members, idt):
				var_fields = [i for i in members if type(i) is ListMember]
				print "    " * idt + "auto %s_buf = cast(ubyte*)&%s;" % (ctx_name,ctx_name)
				if len(var_fields) == 0:
					print "    " * idt + "%s_buf[0..%s.sizeof] = buf[offset_idx..offset_idx+%s.sizeof];" % (ctx_name,ctx_name,ctx_name)
				else:
					print "    " * idt + "%s_buf[0..%s.%s.offsetof] =" % (ctx_name,ctx_name,var_fields[0].name)
					print "    " * (idt+3) + "buf[offset_idx..offset_idx+%s.%s.offsetof];" % (ctx_name,var_fields[0].name)
					print "    " * idt + "offset_idx += %s.%s.offsetof;" % (ctx_name,var_fields[0].name)
				for m in var_fields:
					print
					element_typeinfo = type_registry[m.element_type]
					if element_typeinfo.fixed():
						# dupe slice of elements of fixed type
						print "    " * idt + "%s.%s = (cast(%s*)&buf[offset_idx])[0..%s].dup;" % (
						                      ctx_name,m.name, m.element_type, m.length_expr(ctx_name))
						print "    " * idt + "offset_idx += %s * %s.sizeof;" % (m.length_expr(ctx_name), m.element_type)
					   #if m.type.size % 4 != 0:
						print "    " * idt + "offset_idx += pad4(%s * %s.sizeof);" % (m.length_expr(ctx_name), m.element_type)
					else:
						# allocate array and set each element (vaiable-length)
						print "    " * idt + "%s.%s.length = %s;" % (ctx_name,m.name, m.length_expr(ctx_name))
						item = m.element_type.lower()
						# TODO: const ref?
						print "    " * idt + "foreach (ref %s; %s.%s)" % (item, ctx_name,m.name)
						print "    " * idt + "{"
						nested_from_bytes(item, element_typeinfo.members, idt + 1)  # recursion!
						print "    " * idt + "}"
			print
			print "    " * idt + "this(const ubyte[] buf)"
			print "    " * idt + "{"
			idt += 1
			print "    " * idt + "int offset_idx = 0;"
			nested_from_bytes("this", self.members, idt)  # coid be recursive
			idt -= 1
			print "    " * idt + "}"

		if to_iovec:
			var_fields = [m for m in self.members if type(m) in [ListMember, ValueParamMember]]
			iovec_len = 1 + len(var_fields) + len([m for m in self.members if type(m) is ListMember])
			print
			print "    " * idt + "iovec[%d] toIOVector()" % iovec_len
			print "    " * idt + "{"
			idt += 1
			print "    " * idt + "static immutable byte[3] pad;"
			print "    " * idt + "iovec[%d] parts;" % iovec_len
			print
			part_idx = 0
			print "    " * idt + "parts[%d].iov_base = &this;" % part_idx
			if len(var_fields) == 0:
				print "    " * idt + "parts[%d].iov_len = this.sizeof;" % part_idx
				if self.is_request:
					print "    " * idt + "this.length = cast(ushort)parts[%d].iov_len;" % part_idx
			else:
				print "    " * idt + "parts[%d].iov_len = this.%s.offsetof;" % (part_idx, var_fields[0].offsetof_name())
				if self.is_request:
					print "    " * idt + "this.length = cast(ushort)parts[%d].iov_len;" % part_idx
				part_idx += 1
				for member in var_fields:
					part_idx = member.to_iovec(idt, 'this', part_idx, self.is_request)
				for member in (m for m in self.members if type(m) is ExprFieldMember):
					print
					print "    " * idt + '// TODO: explain this'
					print "    " * idt + "this." + member.name, '=', member.value_expr(self.members) + ';'
			print
			if self.is_request:
				print "    " * idt + "this.length /= 4;"
			print "    " * idt + "return parts;"
			idt -= 1
			print "    " * idt + "}"

		# for structs with padding fields we need custom equality operator
		if len([m for m in self.members if type(m) is PadMember]):  # has pads
			print
			print "    " * idt + "version (unittest)"
			print "    " * idt + "bool opEquals(ref const %s other) const" % self.name
			print "    " * idt + "{"
			idt += 1
			print "    " * idt + "return",
			print ("\n" + "    " * idt + "    && ").join(
				["this.%s == other.%s" % (d[1], d[1]) for m in self.members if type(m) is not PadMember for d in m.declarations()]) + ";"
			idt -= 1
			print "    " * idt + "}"

		idt -= 1
		print "    " * idt + "}"


def tr_name(original):
	if original.isdigit():
		return "_"+original
	return {
		# clashed keywords in D
		'class': 'klass',
		'delete': 'del',
		}.get(original, original)


def tr(original):
	name = {
		'BOOL':   'ubyte',
		'BYTE':   'ubyte', # 8-bit value?
		'INT8':   'byte',
		'INT16':  'short',
		'INT32':  'int',
		'CARD8':  'ubyte',
		'CARD16': 'ushort',
		'CARD32': 'uint',
		# D have builtin type for this
		'CHAR2B': 'wchar',
		# capitalizing of this types cant be easily deducted, so adding exception..
		'RGB': 'RGB',
		'COLORMAP': 'ColorMap',
		'COLORITEM': 'ColorItem',
		'VISUALTYPE': 'VisualType',
		'CHARINFO': 'CharInfo',
		'FONTPROP': 'FontProp',
		'TIMECOORD': 'TimeCoord',
		'PIXMAP': 'PixMap',
		'GCONTEXT': 'GContext',
		'VISUALID': 'VisualID',
		'KEYSYM': 'KeySym',
		'KEYCODE': 'KeyCode',
		'CW': 'CW',
		'GC': 'GC',
		'GX': 'GX',
		}.get(original)
	if name is not None:
		return name
	if original.isupper():
		return original.capitalize()
	return original


def src_options(name):
	options = {}
	if name.endswith('Response') or name in ['Setup', ]:
		options['from_bytes'] = True
	if name.endswith('Request'):
		options['to_iovec'] = True
	return options


def main():
	tree = ElementTree()
	tree.parse("xproto.xml")

	#declarations = dict((i.tag, []) for i in tree.getroot())
	declarations = dict((i, []) for i in ['typedefs','structs','unions','enums','requests','errorcopies','errors','events','eventcopies'])

	for i in tree.getroot():
		if i.tag in ['typedef', 'xidtype', 'xidunion']:
			typedef_typeinfo = TypedefInfo(i)
			declarations['typedefs'].append(typedef_typeinfo)
			type_registry[typedef_typeinfo.name] = typedef_typeinfo
		elif i.tag == 'struct':
			# skipping exceptions
			if i.attrib['name'] in ['CHAR2B',]:
				continue
			struct_typeinfo = StructInfo(i)
			declarations['structs'].append(struct_typeinfo)
			type_registry[struct_typeinfo.name] = struct_typeinfo
		elif i.tag == 'request':
			request_typeinfo = StructInfo(i)
			declarations['requests'].append(request_typeinfo)
			type_registry[request_typeinfo.name] = request_typeinfo
		elif i.tag == 'enum':
			enum_typeinfo = EnumInfo(i)
			declarations['enums'].append(enum_typeinfo)
			type_registry[enum_typeinfo.name] = enum_typeinfo
		#else:
		#	declarations[i.tag].append([i.attrib['name'],])

	print """/* this file is generated by xd/codegen.py */

module xd.xproto;

version (Posix)
{
    //import core.sys.posix.sys.uio: iovec;
}

import xd.util: iovec, pad4, bitcount;
"""

	print
	print "/**"
	print " * typedefs"
	print " */"
	for typedef_typeinfo in declarations['typedefs']:
		typedef_typeinfo.print_src()

	print "\n"
	print "/**"
	print " * structs"
	print " */"
	for struct_typeinfo in declarations['structs']:
		print
		#print "/*"
		#for line in struct_typeinfo.xml.splitlines():
		#	print " *", line
		#print " */"
		struct_typeinfo.print_src(**src_options(struct_typeinfo.name))

	print "\n"
	print "/**"
	print " *unions"
	print " */"
	for union_typeinfo in declarations['unions']:
		print union_typeinfo

	print "\n"
	print "/**"
	print " * enums"
	print " */"
	for enum_typeinfo in declarations['enums']:
		print
		#print "/*"
		#for line in enum_typeinfo.xml.splitlines():
		#	print " *", line
		#print " */"
		enum_typeinfo.print_src()

	print "\n"
	print "/**"
	print " * requests"
	print " */"
	for request_typeinfo in declarations['requests']:
		print
		#print "/*"
		#for line in request_typeinfo.xml.splitlines():
		#	print " *", line
		#print " */"
		request_typeinfo.print_src(to_iovec=True)

	print "\n"
	print "/**"
	print " * errorcopys"
	print " */"
	for errorcopy_typeinfo in declarations['errorcopies']:
		print errorcopy_typeinfo

	print "\n"
	print "/**"
	print " * errors"
	print " */"
	for error_typeinfo in declarations['errors']:
		print error_typeinfo

	print "\n"
	print "/**"
	print " * events"
	print " */"
	for event_typeinfo in declarations['events']:
		print event_typeinfo

	print
	print "/**"
	print " * eventcopies"
	print " */"
	for eventcopy_typeinfo in declarations['eventcopies']:
		print eventcopy_typeinfo


type_registry = {
	'void':    PrimitiveInfo('void'),	# no type
	'bool':    PrimitiveInfo('bool'),	# boolean value
	'byte':    PrimitiveInfo('byte'),	# signed 8 bits
	'ubyte':   PrimitiveInfo('ubyte'),	# unsigned 8 bits
	'short':   PrimitiveInfo('short'),	# signed 16 bits
	'ushort':  PrimitiveInfo('ushort'),	# unsigned 16 bits
	'int':     PrimitiveInfo('int'),	# signed 32 bits
	'uint':    PrimitiveInfo('uint'),	# unsigned 32 bits
	'long':    PrimitiveInfo('long'),	# signed 64 bits
	'ulong':   PrimitiveInfo('ulong'),	# unsigned 64 bits
	#'cent':    PrimitiveInfo('cent'),	# signed 128 bits (reserved for future use)
	#'ucent':   PrimitiveInfo('ucent'),	# unsigned 128 bits (reserved for future use)
	'float':   PrimitiveInfo('float'),	# 32 bit floating point
	'double':  PrimitiveInfo('double'),	# 64 bit floating point
	'real':    PrimitiveInfo('real'),	# largest hardware implemented floating point size (Implementation Note: 80 bits for x86 CPUs) or double size, whichever is larger
	'ifloat':  PrimitiveInfo('ifloat'),	# imaginary float
	'idouble': PrimitiveInfo('idouble'),# imaginary double
	'ireal':   PrimitiveInfo('ireal'),	# imaginary real
	'cfloat':  PrimitiveInfo('cfloat'),	# a complex number of two float values
	'cdouble': PrimitiveInfo('cdouble'),# complex double
	'creal':   PrimitiveInfo('creal'),	# complex real
	'char':    PrimitiveInfo('char'),	# unsigned 8 bit UTF-8
	'wchar':   PrimitiveInfo('wchar'),	# unsigned 16 bit UTF-16
	'dchar':   PrimitiveInfo('dchar'),	# unsigned 32 bit UTF-32
}


if __name__ == '__main__':
	main()
