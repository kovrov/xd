import xd.core;
import xd.xproto;
import xd.xv;


void main()
{
	int scrn;
	char *display_name = NULL;
	xcb_screen_t *screen;

	auto conn = new xd.core.Connection(0);
	// xcb_connect or throw "Unable to open display"

	auto xv_extension = conn.get_reply(conn.send(xd.xv.QueryExtension()));
	// or throw "No X-Video extension"
	writefln("X-Video Extension version %i.%i", xv_extension.major, xv_extension.minor);

	foreach (screen; conn.setup.roots)
	{
		//writefln("screen #%i", i);
		auto adaptors = conn.get_reply(conn.send(xd.xv.QueryAdaptors(screen.root)));
		foreach (adaptor_info; adaptors.info)
		{
			//writefln("  Adaptor #%i: \"%s\"", j, adaptor_info.name);
			writefln("    number of ports: %i", adaptor_info.num_ports);
			writefln("    port base: %i", adaptor_info.base_id);
			writef("    operations supported: ");

			switch (adaptor_info.type & (XCB_XV_TYPE_INPUT_MASK | XCB_XV_TYPE_OUTPUT_MASK))
			{
			  case XCB_XV_TYPE_INPUT_MASK:
				if (adaptor_info.type & XCB_XV_TYPE_VIDEO_MASK)
					writef("PutVideo ");
				if (adaptor_info.type & XCB_XV_TYPE_STILL_MASK)
					writef("PutStill ");
				if (adaptor_info.type & XCB_XV_TYPE_IMAGE_MASK)
					writef("PutImage ");
				break;

			  case XCB_XV_TYPE_OUTPUT_MASK:
				if (adaptor_info.type & XCB_XV_TYPE_VIDEO_MASK)
					writef( "GetVideo ");
				if (adaptor_info.type & XCB_XV_TYPE_STILL_MASK)
					writef("GetStill ");
				break;

			  default:
				writef("none ");
				break;
			}
			writefln("");

			writefln("    supported visuals:");
			foreach (format; adaptor_info.formats)
				writefln("      depth %i, visualID 0x%2x", format.depth, format.visual);

			auto port_attributes = conn.get_reply(conn.send(xd.xv.QueryPortAttributes(adaptor_info.base_id)));

			if (port_attributes.attributes.length == 0)
			{
				writefln("    no port attributes defined");
			}
			else
			{
				writefln("    number of attributes: %i", port_attributes.attributes.length);

				foreach (attribute_info; port_attributes.attributes)
				{
					writefln("      \"%s\" (range %i to %i)", attribute_info.name, attribute_info.min, attribute_info.max);

					if (attribute_info.flags & XCB_XV_ATTRIBUTE_FLAG_SETTABLE)
						writefln("              client settable attribute");

					if (attribute_info.flags & XCB_XV_ATTRIBUTE_FLAG_GETTABLE)
					{
						writef("              client gettable attribute");

						attribute_atom = conn.get_reply(conn.send(InternAtom(true, attribute_info.name)));
						if (attribute_atom.atom != 0)
						{
							auto port_attribute = conn.get_reply(conn.send(xd.xv.GetPortAttribute(adaptor_info.base_id, attribute_atom.atom)));
							writef(" (current value is %i)", port_attribute.value);
						}
						writefln("");
					}
				}
			}

			encodings = conn.get_reply(conn.send(xd.xv.QueryEncodings(adaptor_info.base_id)));
			int ImageEncodings = 0;
			if (encodings.num_encodings)
			{
				foreach (encoding_info; encodings.info)
				{
					if (encoding_info == "XV_IMAGE")
						ImageEncodings++;
				}

				if (encodings.num_encodings - ImageEncodings)
				{
					writefln("    number of encodings: %i", encodings.num_encodings - ImageEncodings);
					foreach (encoding_info; encodings.info)
					{
						if (encoding_info.name == "XV_IMAGE")
						{
							writefln("      encoding ID #%i: \"%*s\"", encoding_info.encoding, strlen(name), name);
							writefln("        size: %i x %i", encoding_info.width, encoding_info.height);
							writefln("        rate: %f", cast(float)encoding_info.rate.numerator / cast(float)encoding_info.rate.denominator);
							free(name);
						}
					}
				}

				if (ImageEncodings && (adaptor_info.type & XCB_XV_TYPE_IMAGE_MASK))
				{
					foreach (encoding_info; encodings.info)
					{
						if (encoding_info == "XV_IMAGE")
						{
							writefln("    maximum XvImage size: %i x %i",	encoding_info.width, encoding_info.height);
							break;
						}
					}

					image_formats = conn.get_reply(conn.send(xd.xv.ListImageFormats(adaptor_info.base_id)));
					writefln("    Number of image formats: %i", image_formats.format.length);
					foreach (image_format_info; image_formats.format)
					{
						char imageName[5] = {0, 0, 0, 0, 0};
						memcpy(imageName, &(image_format_info.id), 4);
						writef("      id: 0x%x", image_format_info.id);

						if (isprint(imageName[0]) && isprint(imageName[1]) && isprint(imageName[2]) && isprint(imageName[3]))
							writefln(" (%s)", imageName);
						else
							writefln("");

						writef("        guid: ");
						writef("%02x",   cast(ubyte)image_format_info.guid[0]);
						writef("%02x",   cast(ubyte)image_format_info.guid[1]);
						writef("%02x",   cast(ubyte)image_format_info.guid[2]);
						writef("%02x-",  cast(ubyte)image_format_info.guid[3]);
						writef("%02x",   cast(ubyte)image_format_info.guid[4]);
						writef("%02x-",  cast(ubyte)image_format_info.guid[5]);
						writef("%02x",   cast(ubyte)image_format_info.guid[6]);
						writef("%02x-",  cast(ubyte)image_format_info.guid[7]);
						writef("%02x",   cast(ubyte)image_format_info.guid[8]);
						writef("%02x-",  cast(ubyte)image_format_info.guid[9]);
						writef("%02x",   cast(ubyte)image_format_info.guid[10]);
						writef("%02x",   cast(ubyte)image_format_info.guid[11]);
						writef("%02x",   cast(ubyte)image_format_info.guid[12]);
						writef("%02x",   cast(ubyte)image_format_info.guid[13]);
						writef("%02x",   cast(ubyte)image_format_info.guid[14]);
						writefln("%02x", cast(ubyte)image_format_info.guid[15]);

						writefln("        bits per pixel: %i", image_format_info.bpp);
						writefln("        number of planes: %i", image_format_info.num_planes);
						writefln("        type: %s (%s)", (image_format_info.type == XCB_XV_IMAGE_FORMAT_INFO_TYPE_RGB) ? "RGB" : "YUV", (image_format_info.format == XCB_XV_IMAGE_FORMAT_INFO_FORMAT_PACKED) ? "packed" : "planar");

						if (image_format_info.type == XCB_XV_IMAGE_FORMAT_INFO_TYPE_RGB)
						{
							writefln("        depth: %i", image_format_info.depth);
							writefln("        red, green, blue masks: 0x%x, 0x%x, 0x%x", image_format_info.red_mask, image_format_info.green_mask, image_format_info.blue_mask);
						}
						else
						{
						}
						xcb_xv_image_format_info_next(&formats_iter);
					}
				}
			}
		}
	}
}
