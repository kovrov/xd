/*
 * dmd xproto.d core.d util.d -run test/connection_info.d
 */

import xd.core;
//import xd.xproto;

void main()
{
	auto conn = new xd.core.Connection(0);

	writefln("	status: %d", conn.setup.status);
	writefln("	protocol_major_version: %d", conn.setup.protocol_major_version);
	writefln("	protocol_minor_version: %d", conn.setup.protocol_minor_version);
	writefln("	release_number: %d", conn.setup.release_number);
	writefln("	resource_id_base: 0x%X", conn.setup.resource_id_base);
	writefln("	resource_id_mask: %b", conn.setup.resource_id_mask);
	writefln("	motion_buffer_size: %d", conn.setup.motion_buffer_size);
	writefln("	maximum_request_length: %d", conn.setup.maximum_request_length);
	writefln("	image_byte_order: %d", conn.setup.image_byte_order);
	writefln("	bitmap_format_bit_order: %d", conn.setup.bitmap_format_bit_order);
	writefln("	bitmap_format_scanline_unit: %d", conn.setup.bitmap_format_scanline_unit);
	writefln("	bitmap_format_scanline_pad: %d", conn.setup.bitmap_format_scanline_pad);
	writefln("	min_keycode: %d", conn.setup.min_keycode);
	writefln("	max_keycode: %d", conn.setup.max_keycode);
	writefln("	vendor: '%s'", conn.setup.vendor);

	writefln("	pixmap_formats:");
	foreach (pixmap_format; conn.setup.pixmap_formats)
		writefln("	    %s", pixmap_format);

	writefln("	roots[0]:");
	writefln("	    root: 0x%X", conn.setup.roots[0].root);
	writefln("	    default_colormap: %s", conn.setup.roots[0].default_colormap);
	writefln("	    white_pixel: %s", conn.setup.roots[0].white_pixel);
	writefln("	    black_pixel: %s", conn.setup.roots[0].black_pixel);
	writefln("	    current_input_masks: %b", conn.setup.roots[0].current_input_masks);
	writefln("	    width_in_pixels: %s", conn.setup.roots[0].width_in_pixels);
	writefln("	    height_in_pixels: %s", conn.setup.roots[0].height_in_pixels);
	writefln("	    width_in_millimeters: %s", conn.setup.roots[0].width_in_millimeters);
	writefln("	    height_in_millimeters: %s", conn.setup.roots[0].height_in_millimeters);
	writefln("	    min_installed_maps: %s", conn.setup.roots[0].min_installed_maps);
	writefln("	    max_installed_maps: %s", conn.setup.roots[0].max_installed_maps);
	writefln("	    root_visual: 0x%X", conn.setup.roots[0].root_visual);
	outer: foreach (depth; conn.setup.roots[0].allowed_depths)
	{
		foreach (visual; depth.visuals)
		{
			if (visual.visual_id == conn.setup.roots[0].root_visual)
			{
				writefln("	        %s", visual);
				break outer;
			}
		}
	}

	writefln("	    backing_stores: %s", conn.setup.roots[0].backing_stores);
	writefln("	    save_unders: %s", conn.setup.roots[0].save_unders);
	writefln("	    root_depth: %s", conn.setup.roots[0].root_depth);
	//writefln("	    allowed_depths_len: %s", conn.setup.roots[0].allowed_depths_len);

	//while (true)
	//	conn.wait_for_event();
}
