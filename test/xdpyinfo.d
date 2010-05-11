//import std.algorithm: find;
import std.stdio;
import std.string;

import xd.core;
import xd.xproto;

/*
void get_input_focus(Connection conn, Window *focus, int *revert_to)
{
	xGetInputFocusReply rep;
	register xReq *req;
	//LockDisplay(conn);
	GetEmptyReq(GetInputFocus, req);
	(void) _XReply (conn, (xReply *)&rep, 0, xTrue);
	*focus = rep.focus;
	*revert_to = rep.revertTo;
	//UnlockDisplay(conn);
	//SyncHandle();
}
*/
void print_display_info(Connection conn)
{
	///writefln("name of display:    %s", DisplayString (conn));
	writefln("version number:    %s.%s", conn.setup.protocol_major_version, conn.setup.protocol_minor_version);
	writefln("vendor string:    %s", conn.setup.vendor);
	writefln("vendor release number:    %d", conn.setup.release_number);

	int vendrel = conn.setup.release_number;
	if (-1 != std.string.indexOf(conn.setup.vendor, "XFree86"))  // strstr(ServerVendor (conn), "XFree86")
	{
		write("XFree86 version: ");
		if (vendrel < 336)
		{
			/*
			 * vendrel was set incorrectly for 3.3.4 and 3.3.5, so handle
			 * those cases here.
			 */
			writef("%d.%d.%d", vendrel / 100, (vendrel / 10) % 10, vendrel % 10);
		}
		else if (vendrel < 3900)
		{
			/* 3.3.x versions, other than the exceptions handled above */
			writef("%d.%d", vendrel / 1000, (vendrel /  100) % 10);
			if (((vendrel / 10) % 10) || (vendrel % 10))
			{
				writef(".%d", (vendrel / 10) % 10);
				if (vendrel % 10)
				{
					writef(".%d", vendrel % 10);
				}
			}
		}
		else if (vendrel < 40000000)
		{
			/* 4.0.x versions */
			writef("%d.%d", vendrel / 1000, (vendrel /   10) % 10);
			if (vendrel % 10) {
				writef(".%d", vendrel % 10);
			}
		}
		else
		{
			/* post-4.0.x */
			writef("%d.%d.%d", vendrel / 10000000, (vendrel / 100000) % 100, (vendrel / 1000) % 100);
			if (vendrel % 1000)
			{
				writef(".%d", vendrel % 1000);
			}
		}
		writeln();
	}

	if (-1 != std.string.indexOf(conn.setup.vendor, "X.Org"))  // strstr(ServerVendor (conn), "X.Org")
	{
		write("X.Org version: ");
		writef("%d.%d.%d", vendrel / 10000000, (vendrel / 100000) % 100, (vendrel / 1000) % 100);
		if (vendrel % 1000)
			writef(".%d", vendrel % 1000);
		writeln();
	}

	if (-1 != std.string.indexOf(conn.setup.vendor, "DMX"))  // strstr(ServerVendor (conn), "DMX")
	{
		int major = vendrel / 100000000;
		vendrel  -= major   * 100000000;
		int minor = vendrel /   1000000;
		vendrel  -= minor   *   1000000;
		int year  = vendrel /     10000;
		vendrel  -= year    *     10000;
		int month = vendrel /       100;
		vendrel  -= month   *       100;
		int day   = vendrel;
								/* Add other epoch tests here */
		if (major > 0 && minor > 0)
			year += 2000;
								/* Do some sanity tests in case there is
								 * another server with the same vendor
								 * string.  That server could easily use
								 * values < 100000000, which would have
								 * the effect of keeping our major
								 * number 0. */
		if (major > 0 && major <= 20
			&& minor >= 0 && minor <= 99
			&& year >= 2000
			&& month >= 1 && month <= 12
			&& day >= 1 && day <= 31)
			writefln("DMX version: %d.%d.%04d%02d%02d", major, minor, year, month, day);
	}

	writefln("maximum request size:  %d bytes", conn.setup.maximum_request_length * 4); // FIXME: BIG-REQUESTS
	writefln("motion buffer size:  %s",  conn.setup.motion_buffer_size);

	writefln("bitmap unit, bit order, padding:    %d, %s, %d",
			conn.setup.bitmap_format_scanline_unit,
			conn.setup.bitmap_format_bit_order == ImageOrder.LSBFirst ? "LSBFirst":
			conn.setup.bitmap_format_bit_order == ImageOrder.MSBFirst ? "MSBFirst": "?",
			conn.setup.bitmap_format_scanline_pad);

	writefln("image byte order:    %s",
			conn.setup.image_byte_order == ImageOrder.LSBFirst ? "LSBFirst":
			conn.setup.image_byte_order == ImageOrder.MSBFirst ? "MSBFirst": "?");

	writefln("number of supported pixmap formats:    %d", conn.setup.pixmap_formats.length);
	writefln("supported pixmap formats:");
	foreach (pixmap_format; conn.setup.pixmap_formats)
	{
		writefln("    depth %d, bits_per_pixel %d, scanline_pad %d",
				pixmap_format.depth, pixmap_format.bits_per_pixel, pixmap_format.scanline_pad);
	}

	/*
	 * when we get interfaces to the PixmapFormat stuff, insert code here
	 */

	writefln("keycode range:    minimum %d, maximum %d", conn.setup.min_keycode, conn.setup.max_keycode);

/**
	GetInputFocus (conn, &focuswin, &focusrevert);  // XGetInputFocus
	writefln("focus:  ");

	switch (focuswin)
	{
	case InputFocus.PointerRoot:
		writefln("PointerRoot");
		break;

	case InputFocus.None:
		writefln("None");
		break;

	default:
		writefln("window 0x%lx, revert to ", focuswin);
		switch (focusrevert)
		{
		case InputFocus.Parent:
			writefln("Parent");
			break;
			case InputFocus.None:
			writefln("None");
			break;

		case InputFocus.PointerRoot:
			writefln("PointerRoot");
			break;

		default:  // should not happen
			writefln("%d", focusrevert);
		}
	}
*/

	///print_extension_info (conn);

	///writefln("default screen number:    %d", DefaultScreen (conn));
	writefln("number of screens:    %d", conn.setup.roots.length);
}


void main()
{
	auto conn = new Connection(0);
	print_display_info(conn);
}
