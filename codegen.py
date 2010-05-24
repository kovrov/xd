from xml.etree.ElementTree import ElementTree, tostring

indent = 1

class PrimitiveInfo:
	def __init__(self, name):
		self.name = name
	def fixed(self):
		#print "#"+' '*indent+"PrimitiveInfo(%s).fixed -> True" % self.name
		return True

class EnumInfo:
	def __init__(self, element):
		self.name = tr(element.attrib['name'])
		self.members = []
		self.xml = tostring(element).strip()
		self.type = None
		for i in element:
			if i[0].tag == 'value':
				init = i[0].text
			elif i[0].tag == 'bit':
				init = i[0].text
			self.members.append([tr_name(i.attrib['name']), init])
	def fixed(self):
		#print "#"+' '*indent+"EnumInfo(%s).fixed -> True" % self.name
		return True
	def src(self):
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
		elif 'xidtype':
			self.name = tr(element.attrib['name'])
			self.type = "uint"
		self.xml = tostring(element).strip()
	def fixed(self):
		#print "#"+' '*indent+"TypedefInfo(%s).fixed -> %s" % (self.name, type_registry[self.type].fixed())
		return type_registry[self.type].fixed()
	def src(self):
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


class PadMember:
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


class ListMember:
	def __init__(self, element, ctx):
		def flatten(em):
			if em.tag == 'op':
				a,b = em
				return '(' + flatten(a) + em.attrib['op'] + flatten(b) + ')'
			assert 0 == len(em)
			assert 0 == len(em.attrib)
			return em.text
		# element[0] is exprfield?
		self.length_expr = flatten(element[0]) if len(element) == 1 else ""
		self.name = tr_name(element.attrib['name'])
		self.element_type = tr(element.attrib['type'])
		self.type = self.element_type + ("[%s]" % self.length_expr if self.length_expr.isdigit() else "[]")
	def fixed(self):
		#print "#"+' '*indent+"ListMember(%s).fixed -> %s" % (self.name, self.length_expr.isdigit())
		return self.length_expr.isdigit()


class ValueParamMember:
	def __init__(self, element, ctx):
		# TODO: complete!
		self.name = tr_name(element.attrib['value-mask-name'])
		self.type = tr_name(element.attrib['value-mask-type'])
'''
uint mask;
uint[] values;
foreach (key; opt.keys.sort)
{
	mask |= key;
	values ~= opt[key];
}
'''

class ReplyMember:
	def __init__(self, element, ctx):
		# TODO: complete!
		self.name = "Reply {}"
		self.type = "struct"


class ExprFieldMember:
	def __init__(self, element, ctx):
		# TODO: complete!
		self.name = tr_name(element.attrib['name'])
		self.type = tr_name(element.attrib['type'])


class StructInfo:
	def __init__(self, element):
		self.name = tr(element.attrib['name'])
		self.members = []
		self.xml = tostring(element).strip()
		ctx = {'structinfo': self} # just in case...
		for i in element:
			member = {'field':FieldMember, 'pad':PadMember, 'list':ListMember, 'valueparam':ValueParamMember, 'reply':ReplyMember, 'exprfield':ExprFieldMember}[i.tag](i, ctx)
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

	def src(self, options):
		idt = 1
		print "struct", self.name
		print "{"
		for member in self.members:
			print "   ", member.type, member.name + ";"

		if 'from_bytes' in options:
			def nested_from_bytes(name, members, idt):
				var_fields = [i for i in members if isinstance(i, ListMember)]
				print "    " * idt + "auto %s_buf = cast(ubyte*)&%s;" % (name,name)
				if len(var_fields) == 0:
					print "    " * idt + "%s_buf[0..%s.sizeof] = buf[offset_idx..offset_idx+%s.sizeof];" % (name,name,name)
				else:
					print "    " * idt + "%s_buf[0..%s.%s.offsetof] =" % (name,name,var_fields[0].name)
					print "    " * (idt+3) + "buf[offset_idx..offset_idx+%s.%s.offsetof];" % (name,var_fields[0].name)
					print "    " * idt + "offset_idx += %s.%s.offsetof;" % (name,var_fields[0].name)
				for m in var_fields:
					print
					element_typeinfo = type_registry[m.element_type]
					if element_typeinfo.fixed():
						# dupe slice of elements of fixed type
						print "    " * idt + "%s.%s = (cast(%s*)&buf[offset_idx])[0..%s.%s].dup;" % (name,m.name, m.element_type, name,m.length_expr)
						print "    " * idt + "offset_idx += %s.%s * %s.sizeof;" % (name,m.length_expr, m.element_type)
					   #if m.type.size % 4 != 0:
						print "    " * idt + "offset_idx += pad4(%s.%s * %s.sizeof);" % (name,m.length_expr, m.element_type)
					else:
						# allocate array and set each element (vaiable-length)
						print "    " * idt + "%s.%s.length = %s.%s;" % (name,m.name, name,m.length_expr)
						item = m.element_type.lower()
						print "    " * idt + "foreach (ref %s; %s.%s)" % (item, name,m.name)
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

		if 'to_iovec' in options:
			def nested_to_iovec(name, members, part_idx, idt):
				var_fields = [m for m in self.members if isinstance(m, ListMember)]
				print "    " * idt + "parts[%d].iov_base = &%s;" % (part_idx, name)
				if len(var_fields) == 0:
					print "    " * idt + "parts[%d].iov_len = %s.sizeof;" % (part_idx, name)
					return
				member = var_fields[0]
				print "    " * idt + "parts[%d].iov_len = %s.%s.offsetof;" % (part_idx, name,member.name)
				part_idx += 1
				for member in var_fields:
					print
					print "    " * idt + "%s.%s = cast(typeof(%s.%s))%s.%s.length;" % (name,member.length_expr, name,member.length_expr, name,member.name)
					print "    " * idt + "parts[%d].iov_base = %s.%s.ptr;" % (part_idx, name,member.name)
					print "    " * idt + "parts[%d].iov_len = %s.%s.length;" % (part_idx, name,member.name)
					part_idx += 1
					print
					print "    " * idt + "parts[%d].iov_base = pad.ptr;" % part_idx
					print "    " * idt + "parts[%d].iov_len = pad4(%s.%s.length);" % (part_idx, name,member.name)
					part_idx += 1

			iovec_len = 1 + len([m for m in self.members if isinstance(m, ListMember)]) * 2 # FIXME:

			print
			print "    " * idt + "iovec[%d] toIOVector()" % iovec_len
			print "    " * idt + "{"
			idt += 1
			print "    " * idt + "byte[3] pad;"
			print "    " * idt + "iovec[%d] parts;" % iovec_len
			print
			nested_to_iovec("this", self.members, 0, idt)
			print
			print "    " * idt + "return parts;"
			idt -= 1
			print "    " * idt + "}"

		print "}"


def tr_name(original):
	if original.isdigit():
		return "_"+original
	return {
		# class is keyword in D
		'class': 'klass',
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
	options = []
	if name.endswith('Response') or name in ['Setup', ]:
		options.append('from_bytes')
	if name.endswith('Request'):
		options.append('to_iovec')
	return options 


def main():
	tree = ElementTree()
	tree.parse("xproto.xml")

	#declarations = dict((i.tag, []) for i in tree.getroot())
	declarations = dict((i, []) for i in ['typedefs','structs','unions','enums','requests','errorcopies','xidunions','errors','events','eventcopies'])

	for i in tree.getroot():
		if i.tag in ['typedef', 'xidtype']:
			typedef_typeinfo = TypedefInfo(i)
			declarations['typedefs'].append(typedef_typeinfo)
			type_registry[typedef_typeinfo.name] = typedef_typeinfo
		elif i.tag in ['struct', 'request']:
			# skipping exceptions
			if i.attrib['name'] in ['CHAR2B',]:
				continue
			struct_typeinfo = StructInfo(i)
			declarations['structs'].append(struct_typeinfo)
			type_registry[struct_typeinfo.name] = struct_typeinfo
		if i.tag == 'enum':
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

import xd.util: iovec, pad4;
"""

	print
	print "/**"
	print " * typedefs"
	print " */"
	for typedef_typeinfo in declarations['typedefs']:
		typedef_typeinfo.src()

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
		struct_typeinfo.src(src_options(struct_typeinfo.name))

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
		enum_typeinfo.src()

	print "\n"
	print "/**"
	print " * requests"
	print " */"
	for request_typeinfo in declarations['requests']:
		print request_typeinfo

	print "\n"
	print "/**"
	print " * errorcopys"
	print " */"
	for errorcopy_typeinfo in declarations['errorcopies']:
		print errorcopy_typeinfo

	print "\n"
	print "/**"
	print " * xidunion"
	print " */"
	for xidunion_typeinfo in declarations['xidunions']:
		print xidunion_typeinfo

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
